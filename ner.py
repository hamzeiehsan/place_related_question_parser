import logging
from tree import AnyNode, Tree
from allennlp import pretrained

logging.basicConfig(level=logging.INFO)
model = pretrained.fine_grained_named_entity_recognition_with_elmo_peters_2018()
parsemodel = pretrained.span_based_constituency_parsing_with_elmo_joshi_2018()

up_name_tags = ['U-GPE', 'U-LOC', 'U-FAC', 'U-ORG']
cp_name_tags = ['B-GPE', 'B-LOC', 'B-FAC', 'B-ORG', 'I-GPE', 'I-LOC', 'I-FAC', 'I-ORG', 'L-GPE', 'L-LOC', 'L-FAC',
                'L-ORG']

u_date_tags = ['U-DATE']
cp_date_tags = ['B-DATE', 'I-DATE', 'L-DATE']

u_event_tags = ['U-EVENT']
cp_event_tags = ['B-EVENT', 'I-EVENT', 'L-EVENT']

noun_phrase_tags = ['NN, NNS']

class NER:
    @staticmethod
    def parse(sentence):
        res = model.predict(sentence=sentence)
        return res

    @staticmethod
    def extract_entities(sentence, u_list, cp_list):
        entities = []
        parsed = NER.parse(sentence)
        current = ''
        for i in range(0, len(parsed['tags'])):
            logging.debug('i: {} word: {} and tag: {}'.format(i, parsed['words'][i], parsed['tags'][i]))
            if parsed['tags'][i] in u_list:
                entities.append(parsed['words'][i])
            elif parsed['tags'][i] in cp_list:
                if parsed['tags'][i].startswith('B-'):
                    current = parsed['words'][i] + ' '
                elif parsed['tags'][i].startswith('L-'):
                    current += parsed['words'][i]
                    entities.append(current)
                else:
                    current += parsed['words'][i] + ' '
        return entities

    @staticmethod
    def extract_place_names(sentence):
        return NER.extract_entities(sentence, up_name_tags, cp_name_tags)

    @staticmethod
    def extract_dates(sentence):
        return NER.extract_entities(sentence, u_date_tags, cp_date_tags)

    @staticmethod
    def extract_events(sentence):
        return NER.extract_entities(sentence, u_event_tags, cp_event_tags)


class CPARSER:
    @staticmethod
    def parse(sentence):
        res = parsemodel.predict(sentence)
        return res['hierplane_tree']['root']

    @staticmethod
    def construct_tree(sentence):
        parse_results = CPARSER.parse(sentence)
        return Tree(parse_results)