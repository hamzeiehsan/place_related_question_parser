from ner import NER, CPARSER, Embedding, DPARSER
from placequestionparsetree import FOLGenerator
from querygenerator import SPARQLGenerator
import re

import logging


logging.basicConfig(level=logging.INFO)

COMPOUNDS_QW = ['How many', 'Are there', 'Is there', 'how many', 'are there', 'is there', 'In which', 'In what',
                'Through which', 'Through what']
COMPOUNDS_QW_ROLE = {'How many':'6', 'Are there':'8', 'Is there':'8', 'In which': '3', 'In what': '2',
                     'Through which': '3', 'Through what': '2'}



# load place type
def load_pt(fpt):
    pt_set = set()
    pt_dict = dict()
    fpt = open(fpt, 'r', encoding="utf8")
    for line in fpt.readlines():
        pt_set.add(line.strip())
        pt_set.add('the '+line.strip())
        pt_dict[line.strip()] = 1
        pt_dict['the '+line.strip()] = 1
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
    # questions.append("In what county is Stonehenge located")
    # questions.append("Which museums are within 3km of Saint George's Hotel in London?")
    # questions.append("Which provinces of Ireland have population over 2000000?")
    # questions.append("What is the population density of cities that are affected by the hurricanes in the USA in the last century")
    # questions.append("Where can I buy coffee and watch movies in Melbourne?")
    # questions.append("Where can I buy coffee and watch movies within five km of my house?")
    # questions.append("What are the large cities in England except London?")
    # questions.append("What is the land between Euphrates and Tigris")
    # questions.append("What is the land between Black Sea, Black Forest and the Danube?")
    # questions.append("Which counties of Ireland does River Shannon cross?")
    # questions.append("What is the most populated city in the United Kingdom except London?")
    # questions.append("Where can I buy the best coffee and see exotic birds near to the Australian National Maritime Museum?")
    # questions.append("Is Mount Everest taller than 1000 miles?")
    # questions.append("Which tourist attractions in London are at most 3 km from St. Anthony the Great and St. John the Baptist church?")
    # questions.append("Which rivers discharge into the Solway Firth?")
    # questions.append("In which part of England is Liverpool located?")
    # questions.append("What is the name of Britain's longest river?")
    # questions.append("Which hotels are in England's capital?")
    # questions.append("What tourist attractions are there in Belfast, Northern Ireland?")
    # questions.append("Which pubs are near Mercure Hotel in Glasgow, Scotland?")
    # questions.append("Which are the main railway stations in Glasgow, Scotland?")

    # questions.append("Which hospital is nearest to Calton Hill in Edinburgh?")
    # questions.append("Which city of England is nearest to London?")
    # questions.append("What is the name of the river that flows under the Queensway Bridge in Liverpool?")
    # questions.append("Which cities or towns of the United Kingdom have a university?")
    # questions.append("What is the longest river in England and Wales?")
    # questions.append("What is the distance between Liverpool and Glasgow?")
    # questions.append("Are there any rivers that cross both England and Wales?")
    # questions.append("Which cafes in London are at most 3 km from St. Anthony the Great and "
    #                  "St. John the Baptist church?")
    # questions.append("What is the most populated city in the United Kingdom except London?")

    # questions.append("Where is the closest market to Elephant and Castle underground station?")
    # questions.append("Which is the highest building in London?")
    # questions.append("What is the longest bridge in Scotland?")
    # questions.append("Which is the largest royal borough of London??")
    # questions.append("Which city in Scotland has the largest population?")

    # questions.append("Is the county of Antrim bigger than the county of Armagh?")
    # questions.append("Is there a mountain in the county of Greater Manchester taller than 1300 meters above sea level?")
    # questions.append("Are there more than 10 districts in Hampshire, England?")
    # questions.append("Which rivers in Scotland have more than 100 km length?")
    # questions.append("Is there a river in Ireland that crosses more than 3 cities?")
    # questions.append("Which mountains in Scotland have height more than 1000 meters?")

    questions.append("Which cafes in London are at most 3 km from St. Anthony the Great and St. John the Baptist church")

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
                if type+' '+specific in whole_question:
                    captured.append(type+' '+specific)
                elif specific+' '+type in whole_question:
                    captured.append(specific+' '+type)
                elif not type.endswith("s") and 'the '+type+' of '+ specific in whole_question: # not plural and have the pattern the type of P
                    captured.append('the '+type+' of '+ specific)
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
                res[comp+'--'+str(question.index(comp))] = {'start':question.index(comp),
                                                            'end':question.index(comp)+len(comp),
                                                            'role':COMPOUNDS_QW_ROLE[comp], 'pos': 'ADV'}
            else:
                res[comp+'--'+str(question.index(comp))] = {'start': question.index(comp),
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
                    labelled[v+'--'+str(position[0])] = {'start': position[0],
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
    for k1,v1 in info.items():
        correct = True
        for k2,v2 in info.items():
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
            if t+', '+t2 in question:
                question = question.replace(t+', '+t2, t+' in '+t2)
        for t2 in types:
            if t+"'s "+t2 in question:
                question = question.replace(t+"'s "+t2, 'the ' + t2+' of '+t)

    return question


PRONOUN = dict(
    {'Where': '1', 'What': '2', 'Which': '3', 'When': '4', 'How': '5', 'Why': '7', 'Does': '8',
     'Is': '8', 'Are': '8', 'Do': '8'})
CONDITIONAL = ['are', 'is', 'was', 'were', 'did', 'do', 'does']

ENCODINGS = dict(
    {'toponyms': 'P', 'place_types': 'p', 'events': 'E', 'event_types': 'e', 'dates': 'd', 'spatial_relationship': 'r',
     'qualities': 'q', 'activities': 'a', 'situations': 's', 'non-platial_objects': 'o'})

COMPARISON = {'more than': '>', 'less than': '<', 'greater than': '>', 'smaller than': '<', 'equal to': '=',
              'at most': '<=', 'at least': '>=', 'over': '>'}

COMPARISON_REGEX = {'more .* than': 'more than', 'less .* than':'less than', 'greater .* than': 'greater than',
                    'smaller .* than': 'smaller than'}

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

logging.info('reading dataset...')
questions = load_dataset('data/datasets/GeoQuestion201.csv')
questions = load_dummy_dataset()  # if you want to just test! check the function...


def analyze(questions):
    for question in questions:
        # extract NER using fine-grained NER model
        result = extract_information(question, pt_set, et_set)
        logging.info('NER extracts: \n'+str(result))
        question = refine_questions(question, result['toponyms'], result['place_types'])

        # construct and constituency tree dependency tree
        tree = CPARSER.construct_tree(question)

        logging.debug('initial constituency tree:\n' + str(tree))
        labelled = {}
        for k, v in PRONOUN.items():
            if question.startswith(k + ' '):
                tree.label_role(k, v, question_words=True)
                labelled[k+"--"+str(question.index(k))] = {'start': question.index(k),
                                                           'end': question.index(k)+len(k), 'role': v, 'pos': 'ADV'}
        compound_qw = find_compound_question_words(question)
        for qw in compound_qw.keys():
            role = ''
            if re.split('--', qw.strip())[0] in COMPOUNDS_QW_ROLE.keys():
                role = COMPOUNDS_QW_ROLE[re.split('--', qw.strip())[0]]
            tree.label_role(re.split('--', qw.strip())[0], role, clean=True, question_words=True)
        labelled = {**labelled, **compound_qw}

        ners = construct_cleaning_labels(result, question)
        logging.info('clean ners:\n'+str(ners))

        for k,v in ners.items():
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
                labelled[c+'--'+str(question.index(c))] = {'start': question.index(c),
                                                           'end': question.index(c) + len(c),
                                                            'role': v, 'pos': 'ADJ'}
        for creg, c in COMPARISON_REGEX.items():
            reg_search = re.search(creg, question)
            if reg_search is not None:
                tree.label_complex_comparison(reg_search, c, COMPARISON[c])
                labelled[c+'--'+str(reg_search.regs[0][0])] = {'start': reg_search.regs[0][0],
                                                               'end': reg_search.regs[0][1], 'role': COMPARISON[c],
                                                               'pos': 'ADJ'}

        tree.label_events_actions()
        tree.clean_phrases()
        logging.info('constituency tree:\n' + str(tree))
        labelled = clean_extracted_info(labelled)
        logging.info('encoded elements:\n' + str(labelled))

        # construct dependency tree, cleaning
        d_tree = DPARSER.construct_tree(question)
        logging.debug('initial dependency tree:\n' + str(d_tree))

        d_tree.clean_d_tree(labelled)
        logging.info('refined dependency tree:\n'+str(d_tree))

        # use FOLGenerator to detect dependencies inside both parsing trees
        # intent recognition
        # generate FOL statements based on deps (FOLGenerator class)
        fol = FOLGenerator(cons_tree=tree, dep_tree=d_tree)
        fol.generate_dependencies()

        fol.print_dependencies()

        # print FOL statements
        # todo define variables (p, e, o); implicit (where - situations/activities);
        #  define properties and constants; define relationships, comparison
        fol.print_logical_form()


        # generate GeoSPARQL queries from FOL statements (deps)
        generator = SPARQLGenerator(fol.dependencies, fol.variables)

        print(generator.to_SPARQL())


analyze(questions)
