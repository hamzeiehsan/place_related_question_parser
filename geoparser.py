from ner import NER, CPARSER, Embedding, DPARSER

import logging


logging.basicConfig(level=logging.INFO)


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


# find toponyms
def find_toponyms(question):
    return NER.extract_place_names(question)


# find events
def find_events(question):
    return NER.extract_events(question)


# find place types and event types
def find_types(question, excluded, types):
    for ex in excluded:
        question = question.replace(ex, '')
    question = question.lower().strip()
    captured = []
    for type in types:
        if type in question:
            captured.append(type)
    captured = sorted(captured, key=len, reverse=True)
    final_list = []
    concat = ''
    for type in captured:
        if len(final_list) == 0 or type not in concat:
            final_list.append(type)
            concat+=type+' '
    return final_list


# find dates
def find_dates(question):
    return NER.extract_dates(question)


# extract information
def extract_information(question, ptypes, etypes):
    toponyms = find_toponyms(question)
    events = find_events(question)
    dates = find_dates(question)

    excluded = []
    excluded.extend(toponyms)
    excluded.extend(events)
    excluded.extend(dates)

    place_types = find_types(question, excluded, ptypes)

    excluded.extend(place_types)

    event_types = find_types(question, excluded, etypes)

    results = {}
    results['toponyms'] = toponyms
    results['events'] = events
    results['dates'] = dates
    results['place_types'] = place_types
    results['event_types'] = event_types

    return results


PRONOUN = dict(
    {'where': '1', 'what': '2', 'which': '3', 'when': '4', 'why': '7'})
CONDITIONAL = ['are', 'is', 'was', 'were', 'did', 'do', 'does']

ENCODINGS = dict(
    {'toponyms': 'P', 'place_types': 'p', 'events': 'E', 'event_types': 'e', 'dates': 'd', 'spatial_relationship': 'r',
     'qualities': 'q', 'activities': 'a', 'situations': 's', 'non-platial_objects': 'o'})

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

logging.info('The program starts to parse test samples')

# question = "What is the population density of cities that are affected by the hurricanes in the USA in the last century"
# question = "Where can I buy coffee and watch movies in Melbourne?"
# question = "Where can I buy coffee and watch movies within five km of my house?"
# question = "What are the large cities in England except London?"
# question = "What is the land between Euphrates and Tigris"
# question = "What is the land between Black Sea, Black Forest and the Danube?"
# question = "Which counties of Ireland does River Shannon cross?"
# question = "What is the most populated city in the United Kingdom except London?"
# question = "Where can I buy the best coffee and see exotic birds near to the Australian National Maritime Museum?"
# question ="Is Mount Everest taller than 1000 miles?"
question ="Which tourist attractions in London are at most 3 km from St. Anthony the Great and St. John the Baptist church?"

# extract NER using fine-grained NER model
result = extract_information(question, pt_set, et_set)

# construct and constituency tree dependency tree
tree = CPARSER.construct_tree(question)

logging.info('tree:\n'+str(tree))
multi_words = {}
for k,v in ENCODINGS.items():
    if k in result.keys():
        for item in result[k]:
            status = tree.label_role(item, v, clean=True)
            if status is False:
                logging.error('error in finding {} in the tree'.format(item))
            if len(item.split(' ')) > 1:
                multi_words[item] = {'start':question.index(item), 'end':question.index(item)+len(item)}

multi_word_npo = tree.label_tree()

verbs = tree.get_verbs()
decisions = Embedding.verb_encoding(tree.root.name, verbs)
tree.label_situation_activities(verbs=verbs, decisions=decisions)
tree.label_events_actions()

logging.info('tree:\n'+str(tree))

# construct dependency tree, cleaning and extract dependencies
d_tree = DPARSER.construct_tree(question)
d_tree.clean_d_tree(multi_words)
d_tree.clean_d_tree(multi_word_npo)
print(d_tree)
d_tree.detect_dependencies()

# update constituency tree with dependencies
tree.apply_dependencies(d_tree.dependencies)
print('tree:\n'+str(tree))