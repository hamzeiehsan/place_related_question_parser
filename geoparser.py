from ner import NER, CPARSER, Embedding, DPARSER
from placequestionparsetree import FOLGenerator
from querygenerator import SPARQLGenerator
import re
import json
import logging

logging.basicConfig(level=logging.INFO)

COMPOUNDS_QW = ['How many', 'Are there', 'Is there', 'how many', 'are there', 'is there', 'In which', 'In what',
                'Through which', 'Through what']
COMPOUNDS_QW_ROLE = {'How many': '6', 'Are there': '8', 'Is there': '8', 'In which': '3', 'In what': '2',
                     'Through which': '3', 'Through what': '2'}


# load place type
def load_pt(fpt):
    pt_set = set()
    pt_dict = dict()
    fpt = open(fpt, 'r', encoding="utf8")
    for line in fpt.readlines():
        pt_set.add(line.strip())
        pt_set.add('the ' + line.strip())
        pt_dict[line.strip()] = 1
        pt_dict['the ' + line.strip()] = 1
    fpt.close()
    return pt_set, pt_dict


# load word
def load_word(fword):
    words = set()
    fword = open(fword, 'r', encoding="utf8")
    for line in fword.readlines():
        word = line.strip()
        words.add(word)
    fword.close()
    return words


# load dataset
def load_dataset(path):
    questions = []
    fdataset = open(path, 'r', encoding='utf-8-sig')
    for line in fdataset.readlines():
        questions.append(line)
    fdataset.close()
    return questions


def load_dummy_dataset():
    questions = []
    questions.extend(["Is county Oxfordshire east of the county Essex?",
                      "Is the Castle of Edinburgh less than 2 km away from Calton Hill?",
                      "Does England have more counties than Ireland?",
                      "Which site of Manchester is the most popular?",
                      "In which city is Big Ben located?",
                      "Is there mountain in the county of Greater Manchester taller than 1300 meters above sea level?",
                      "What is the most populated city in the United Kingdom except London?"])

    return questions


# find toponyms
def find_toponyms(question):
    return NER.extract_place_names(question)


# find events
def find_events(question):
    return NER.extract_events(question)


# find place types and event types
def find_types(question, excluded, types, specifics=[]):
    whole_question = question
    for ex in excluded:
        question = question.replace(ex, '')
    question = question.lower().strip()
    captured = []
    for type in types:
        if type in question:
            captured.append(type)
            for specific in specifics:
                if type + ' ' + specific in whole_question:
                    captured.append(type + ' ' + specific)
                elif specific + ' ' + type in whole_question:
                    captured.append(specific + ' ' + type)
                elif not type.endswith(
                        "s") and 'the ' + type + ' of ' + specific in whole_question:
                    captured.append('the ' + type + ' of ' + specific)
    captured = sorted(captured, key=len, reverse=True)
    return captured


# find dates
def find_dates(question):
    return NER.extract_dates(question)


def find_compound_question_words(question):
    res = {}
    for comp in COMPOUNDS_QW:
        if comp in question:
            if comp in COMPOUNDS_QW_ROLE.keys():
                res[comp + '--' + str(question.index(comp))] = {'start': question.index(comp),
                                                                'end': question.index(comp) + len(comp),
                                                                'role': COMPOUNDS_QW_ROLE[comp], 'pos': 'ADV'}
            else:
                res[comp + '--' + str(question.index(comp))] = {'start': question.index(comp),
                                                                'end': question.index(comp) + len(comp),
                                                                'role': '', 'pos': 'ADV'}
    return res


# extract information
def extract_information(question, ptypes, etypes):
    toponyms = find_toponyms(question)
    events = find_events(question)
    dates = find_dates(question)

    excluded = []
    excluded.extend(toponyms)
    excluded.extend(events)
    excluded.extend(dates)

    place_types = find_types(question, excluded, ptypes, toponyms)
    for toponym in toponyms:
        for place_type in place_types:
            if toponym in place_type:
                idx = toponyms.index(toponym)
                toponyms[idx] = place_type
                idx = place_types.index(place_type)
                del place_types[idx]
                break
    excluded.extend(place_types)

    event_types = find_types(question, excluded, etypes, events)
    for event in events:
        for type in event_types:
            if event in type:
                events[events.index(event)] = type
                del event_types[event_types.index(type)]
                break
    results = {}
    results['toponyms'] = toponyms
    results['events'] = events
    results['dates'] = dates
    results['place_types'] = place_types
    results['event_types'] = event_types

    return results


def construct_cleaning_labels(results, question):
    orders = ['toponyms', 'events', 'dates', 'place_types', 'event_types']
    indices = []
    labelled = {}
    for order in orders:
        values = results[order]
        role = ENCODINGS[order]
        for v in values:
            temp = v
            if temp not in question:
                temp = temp.replace(" 's", "'s")
            matches = re.finditer(temp, question)
            matches_positions = [[match.start(), match.end()] for match in matches]
            for position in matches_positions:
                if not is_overlap(position, indices):
                    labelled[v + '--' + str(position[0])] = {'start': position[0],
                                                             'end': position[1],
                                                             'role': role,
                                                             'pos': 'NOUN'}
            indices.extend(matches_positions)
    return labelled


def is_overlap(position, indices):
    for index in indices:
        if position[0] >= index[0] and position[1] <= index[1]:
            return True
    return False


def clean_extracted_info(info):
    clean_info = {}
    for k1, v1 in info.items():
        correct = True
        for k2, v2 in info.items():
            if k1 != k2:
                if re.split('--', k1.strip())[0] in k2 and v1['start'] >= v2['start'] and v1['end'] <= v2['end']:
                    correct = False
                    break
        if correct:
            clean_info[k1] = v1
    return clean_info


# standardization of addresses and 's as containment
def refine_questions(question, toponyms, types):
    for t in toponyms:
        for t2 in toponyms:
            if t + ', ' + t2 in question:
                question = question.replace(t + ', ' + t2, t + ' in ' + t2)
        for t2 in types:
            if t + "'s " + t2 in question:
                question = question.replace(t + "'s " + t2, 'the ' + t2 + ' of ' + t)

    for key, pattern in SUPERLATIVE_SP_REGEX.items():
        reg_search = re.search(pattern, question)
        if reg_search is not None:
            current = question[reg_search.regs[0][0]: reg_search.regs[0][1]]
            refined = reg_search.group(1) + ' ' + key
            question = question.replace(current, refined)

    return question


def write_labels():
    with open('evaluation/eval.json', "w", encoding='utf-8') as jsonfile:
        json.dump(eval, jsonfile, ensure_ascii=False)


def read_labels():
    with open('evaluation/eval.json', encoding='utf-8') as jsonfile:
        data = json.load(jsonfile)
    return data


def append_to_file(string):
    with open('console.txt', 'a') as redf:
        redf.write(string)


def clean_file():
    with open('console.txt', 'w') as redf:
        redf.write("")


def ask_eval_input(key):
    res = {}
    f = lambda x: '' if x is None else x
    res['TP'] = f(input('how many {} are correctly detected?'.format(key)))
    res['FP'] = f(input('how many {} are incorrectly detected?'.format(key)))
    res['FN'] = f(input('how many {} are missing?'.format(key)))
    return res


PRONOUN = dict(
    {'Where': '1', 'What': '2', 'Which': '3', 'When': '4', 'How': '5', 'Why': '7', 'Does': '8',
     'Is': '8', 'Are': '8', 'Do': '8'})
CONDITIONAL = ['are', 'is', 'was', 'were', 'did', 'do', 'does']

ENCODINGS = dict(
    {'toponyms': 'P', 'place_types': 'p', 'events': 'E', 'event_types': 'e', 'dates': 'd', 'spatial_relationship': 'r',
     'qualities': 'q', 'activities': 'a', 'situations': 's', 'non-platial_objects': 'o'})

COMPARISON = {'more than': '>', 'less than': '<', 'greater than': '>', 'smaller than': '<', 'equal to': '=',
              'at most': '<=', 'at least': '>=', 'over': '>'}

COMPARISON_REGEX = {'more .* than': 'more than', 'less .* than': 'less than', 'greater .* than': 'greater than',
                    'smaller .* than': 'smaller than'}

SUPERLATIVE_SP_REGEX = {'nearest to': 'nearest (.*) to', 'closest to': 'closest (.*) to',
                        'farthest to': 'farthest (.*) to'}

fpt = 'data/place_type/type-set.txt'
factv = 'data/verb/action_verb.txt'
fstav = 'data/verb/stative_verb.txt'
fcountries = 'data/gazetteer/countries.txt'
fet = 'data/event_type/event_types'

pt_set, pt_dict = load_pt(fpt)
et_set, et_dict = load_pt(fet)
actv = load_word(factv)
stav = load_word(fstav)
countries = load_word(fcountries)

Embedding.set_stative_active_words(stav, actv)

is_console = False  # WRITE THE CONSOLE INTO FILE IF TRUE
is_test = False  # IF TRUE: ONLY READ DUMMY QUESTIONS AND RUN THE PROGRAM
is_eval = True  # IF TURE: RUN EVALUATION PER QUESTION, ALSO WRITE THE RESULTS IN EVAL.JSON

logging.info('running parameters: test: {0}, console: {1}, eval: {2}'.format(str(is_test), str(is_console),
                                                                             str(is_eval)))
logging.info('reading dataset...')
if not is_test:
    questions = load_dataset('data/datasets/GeoQuestion201.csv')
    questions = questions[:101]
else:
    questions = load_dummy_dataset()  # if you want to just test! check the function...

eval = {}
if is_eval:
    eval = read_labels()  # question: encoding: {elem: {TP: , FP:, FN: }},
    #                                 fol: {elem: {TP: , FP:, FN: }},
    #                                 geosparql: {elem: {TP: , FP:, FN: }}
    eval_fol = ['Declaration', 'Intent', 'SRelation', 'Situation', 'Comparison', 'Quality', 'Conjunction']
    eval_geosparql = ['Overall', 'Intent', 'Where', 'OrderBy', 'GroupBy']


def analyze(questions):
    clean_file()
    for question in questions:
        original_question = question
        console = '*********************************************\n'
        # extract NER using fine-grained NER model
        result = extract_information(question, pt_set, et_set)
        logging.info('NER extracts: \n' + str(result))
        question = refine_questions(question, result['toponyms'], result['place_types'])

        # construct and constituency tree dependency tree
        tree = CPARSER.construct_tree(question)

        logging.debug('initial constituency tree:\n' + str(tree))
        labelled = {}
        for k, v in PRONOUN.items():
            if question.startswith(k + ' '):
                tree.label_role(k, v, question_words=True)
                labelled[k + "--" + str(question.index(k))] = {'start': question.index(k),
                                                               'end': question.index(k) + len(k), 'role': v,
                                                               'pos': 'ADV'}
        compound_qw = find_compound_question_words(question)
        for qw in compound_qw.keys():
            role = ''
            if re.split('--', qw.strip())[0] in COMPOUNDS_QW_ROLE.keys():
                role = COMPOUNDS_QW_ROLE[re.split('--', qw.strip())[0]]
            tree.label_role(re.split('--', qw.strip())[0], role, clean=True, question_words=True)
        labelled = {**labelled, **compound_qw}

        ners = construct_cleaning_labels(result, question)
        logging.info('clean ners:\n' + str(ners))
        console += str(ners) + '\n'

        for k, v in ners.items():
            tree.label_role(re.split('--', k.strip())[0], v['role'], clean=True)

        labelled = {**labelled, **ners}
        labelled = {**labelled, **tree.label_tree()}

        verbs = tree.get_verbs()
        decisions = Embedding.verb_encoding(tree.root.name, verbs)
        labelled = {**labelled, **tree.label_situation_activities(verbs=verbs, decisions=decisions)}
        tree.label_events_actions()
        labelled = {**labelled, **tree.label_qualities()}
        tree.clean_phrases()
        tree.clean_tree()

        labelled = {**labelled, **tree.label_spatiotemporal_relationships()}

        for c, v in COMPARISON.items():
            if c in question:
                tree.label_role(c, v, comparison=True)
                labelled[c + '--' + str(question.index(c))] = {'start': question.index(c),
                                                               'end': question.index(c) + len(c),
                                                               'role': v, 'pos': 'ADJ'}
        for creg, c in COMPARISON_REGEX.items():
            reg_search = re.search(creg, question)
            if reg_search is not None:
                tree.label_complex_comparison(reg_search, c, COMPARISON[c])
                labelled[c + '--' + str(reg_search.regs[0][0])] = {'start': reg_search.regs[0][0],
                                                                   'end': reg_search.regs[0][1], 'role': COMPARISON[c],
                                                                   'pos': 'ADJ'}

        tree.label_events_actions()
        tree.clean_phrases()
        logging.info('constituency tree:\n' + str(tree))
        labelled = clean_extracted_info(labelled)
        logging.info('encoded elements:\n' + str(labelled))
        console += str(tree) + '\n'

        # construct dependency tree, cleaning
        d_tree = DPARSER.construct_tree(question)
        logging.debug('initial dependency tree:\n' + str(d_tree))

        d_tree.clean_d_tree(labelled)
        logging.info('refined dependency tree:\n' + str(d_tree))
        console += str(d_tree) + '\n'

        # use FOLGenerator to detect dependencies inside both parsing trees
        # intent recognition
        # generate FOL statements based on deps (FOLGenerator class)
        fol = FOLGenerator(cons_tree=tree, dep_tree=d_tree)
        fol.generate_dependencies()

        dep_strings = fol.print_dependencies()
        console += dep_strings + '\n'

        # print FOL statements
        log_string = fol.print_logical_form()
        console += log_string + '\n'

        # generate GeoSPARQL queries from FOL statements (deps)
        generator = SPARQLGenerator(fol.dependencies, fol.variables)
        geosparql = generator.to_SPARQL()
        print(geosparql)
        console += geosparql + '\n\n\n'
        if is_console:
            append_to_file(console)

        if is_eval and question not in eval.keys():
            eval[question] = {'encoding': {}, 'fol': {}, 'geosparql': {}}
            print(question)
            encodings = tree.all_encodings()
            for key, encoding in encodings.items():
                print('evaluate: {}'.format(key))
                print('val: {}'.format(encoding))
                res_eval = ask_eval_input(key)
                eval[question]['encoding'][key] = res_eval
            missing = input('is an encoding missing? (Y/N)')
            while missing == 'Y':
                key = input('what class is missing?')
                if key != "":
                    eval[question]['encoding'][key] = {}
                    eval[question]['encoding'][key]['TP'] = 0
                    eval[question]['encoding'][key]['FP'] = 0
                    f = lambda x: '' if x is None else x
                    eval[question]['encoding'][key]['FN'] = f(input('how many {} is missing?'.format(key)))
                missing = input('is an encoding missing? (Y/N)')

            print(log_string)
            for key in eval_fol:
                print('evaluate based on: {}'.format(key))
                res_eval = ask_eval_input(key)
                eval[question]['fol'][key] = res_eval
            print(geosparql)
            for key in eval_geosparql:
                print('evaluate based on: {}'.format(key))
                res_eval = ask_eval_input(key)
                eval[question]['geosparql'][key] = res_eval
            write = input('Do you want to write into file? (Y/N)')
            if questions.index(original_question) % 20 == 0 or write == 'Y':
                write_labels()
                print('Congrats, you finished evaluating {0} questions, remaining {1}'
                      .format(questions.index(original_question),
                              len(questions) - questions.index(original_question) - 1))
    write_labels()


analyze(questions)


def add_measures(dict_question, dict_all):
    TP = to_int(dict_question['TP'])
    FP = to_int(dict_question['FP'])
    FN = to_int(dict_question['FN'])
    PR = 0
    RC = 0
    dict_all['TP'] += TP
    dict_all['FP'] += FP
    dict_all['FN'] += FN
    dict_all['COUNT'] += 1
    if TP + FP > 0:
        PR = TP / (TP + FP)
        dict_all['PR'] += PR
        dict_all['COUNT_PR'] += 1

    if TP + FN > 0:
        RC = TP / (TP + FN)
        dict_all['RC'] += RC
        dict_all['COUNT_RC'] += 1

    if PR != 0 and RC != 0:
        dict_all['FS'] += 2*PR*RC/(PR+RC)
    return dict_all


KEY_MAPPING = {'1':'Q-Word','2':'Q-Word','3':'Q-Word','4':'Q-Word','5':'Q-Word','6':'Q-Word','7':'Q-Word','8':'Q-Word',
               '<':'<>', '<=':'<>', '>':'<>', '>=':'<>'}


def add_question_measures(eval_question, dict_all, mapping=False):
    for key, val_dict in eval_question.items():
        key2 = key
        if mapping and key in KEY_MAPPING.keys():
            key2 = KEY_MAPPING[key]
        if key2 not in dict_all.keys():
            dict_all[key2] = {'TP': 0, 'FP': 0, 'FN': 0, 'COUNT': 0,
                             'PR': 0, 'COUNT_PR': 0, 'RC': 0, 'COUNT_RC': 0, 'FS': 0}
        dict_all[key2] = add_measures(val_dict, dict_all[key2])
    return dict_all


def calculate_mic_mac_measures(dict_all, only_precision=False):
    new_dict = {}
    if not only_precision:
        print('KEY\t\t\tMAC_PR\t\tMAC_RC\t\tMAC_FS\t\t\tMIC_PR\t\tMIC_RC\t\tMIC_FS')
    else:
        print('KEY\t\t\tMAC_PR\t\t\tMIC_PR')
    for key, val_dict in dict_all.items():
        new_dict[key] = {}
        new_dict[key]['MAC_PR'] = val_dict['PR'] / val_dict['COUNT_PR'] * 100
        if not only_precision:
            new_dict[key]['MAC_RC'] = val_dict['RC'] / val_dict['COUNT_RC'] * 100
            new_dict[key]['MAC_FS'] = val_dict['FS'] / val_dict['COUNT_RC']
        new_dict[key]['MIC_PR'] = val_dict['TP'] / (val_dict['TP'] + val_dict['FP']) * 100
        if not only_precision:
            new_dict[key]['MIC_RC'] = val_dict['TP'] / (val_dict['TP'] + val_dict['FN']) * 100
            new_dict[key]['MIC_FS'] = 2*new_dict[key]['MIC_RC']*new_dict[key]['MIC_PR']/\
                                      (new_dict[key]['MIC_RC']+new_dict[key]['MIC_PR'])
            print('{0: >12}\t{1:2.2f}\t\t{2:2.2f}\t\t{3:2.2f}\t\t\t{4:2.2f}\t\t{5:2.2f}\t\t{6:2.2f}'.
                  format(key, new_dict[key]['MAC_PR'], new_dict[key]['MAC_RC'], new_dict[key]['MAC_FS'],
                         new_dict[key]['MIC_PR'], new_dict[key]['MIC_RC'], new_dict[key]['MIC_FS']))
        else:
            print('{0: >12}\t{1:2.2f}\t\t\t{2:2.2f}'.
                  format(key, new_dict[key]['MAC_PR'], new_dict[key]['MIC_PR']))
    print('---------------------------------------------------------------------------------------------------------\n')
    return new_dict


def to_int(string):
    if isinstance(string, int):
        return string
    if string.strip() == '':
        return 0
    return int(string)


if is_eval:
    logging.info('reading manually investigated results to derive evaluation measure...')
    encoding_evaluation = {}
    fol_evaluation = {}
    geosparql_evaluation = {}
    for question in eval.keys():
        # encoding precision, recall and f-score...
        encoding_evaluation = add_question_measures(eval[question]['encoding'], encoding_evaluation, mapping=True)

        # encoding precision, recall and f-score: for intent only accuracy
        fol_evaluation = add_question_measures(eval[question]['fol'], fol_evaluation)

        # accuracy for overall, intent, where, order by, group by
        geosparql_evaluation = add_question_measures(eval[question]['geosparql'], geosparql_evaluation)

    encodings_results = calculate_mic_mac_measures(encoding_evaluation)
    fol_results = calculate_mic_mac_measures(fol_evaluation)
    geosparql_results = calculate_mic_mac_measures(geosparql_evaluation, only_precision=True)
