import logging

import sklearn

from placequestionparsetree import AnyNode, PlaceQuestionParseTree
from allennlp.predictors.predictor import Predictor
import allennlp_models.rc
from allennlp.modules.elmo import Elmo, batch_to_ids

logging.basicConfig(level=logging.INFO)
model = Predictor.from_path("https://storage.googleapis.com/allennlp-public-models/ner-model-2020.02.10.tar.gz")
parsemodel = Predictor.from_path("https://storage.googleapis.com/allennlp-public-models/elmo-constituency-parser-2020.02.10.tar.gz")
dependencymodel = Predictor.from_path("https://storage.googleapis.com/allennlp-public-models/biaffine-dependency-parser-ptb-2020.04.06.tar.gz")

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
        return PlaceQuestionParseTree(parse_results)


class Embedding:
    # loading ELMo pretrained word embedding model
    options_file = "https://s3-us-west-2.amazonaws.com/allennlp/models/elmo/2x4096_512_2048cnn_2xhighway/elmo_2x4096_512_2048cnn_2xhighway_options.json"
    weight_file = "https://s3-us-west-2.amazonaws.com/allennlp/models/elmo/2x4096_512_2048cnn_2xhighway/elmo_2x4096_512_2048cnn_2xhighway_weights.hdf5"

    elmo = Elmo(options_file, weight_file, 2, dropout=0)

    activity_embs = None
    situation_embs = None

    @staticmethod
    def verb_encoding(sentence, verbs):
        if not Embedding.is_loaded():
            raise RuntimeError from None
        decisions = []
        emb = Embedding.elmo(batch_to_ids([sentence.split()]))['elmo_representations'][0].detach().numpy()
        for verb in verbs:
            v_index = sentence.split().index(verb)
            verb_emb = [emb[0][v_index]]
            stav_similar = sklearn.metrics.pairwise.cosine_similarity(Embedding.situation_embs.squeeze(),
                                                                      verb_emb).max()
            actv_similar = sklearn.metrics.pairwise.cosine_similarity(Embedding.activity_embs.squeeze(), verb_emb).max()
            if actv_similar > max(stav_similar, 0.5):
                decisions.append('a')
            elif stav_similar > max(actv_similar, 0.5):
                decisions.append('s')
            else:
                decisions.append('u')
        return decisions

    @staticmethod
    def set_stative_active_words(stative, active):
        # Verb Elmo representation
        Embedding.activity_embs = Embedding.elmo(batch_to_ids([[v] for v in active]))['elmo_representations'][0].detach().numpy()
        Embedding.situation_embs = Embedding.elmo(batch_to_ids([[v] for v in stative]))['elmo_representations'][0].detach().numpy()

    @staticmethod
    def is_loaded():
        if Embedding.situation_embs is None or Embedding.activity_embs is None:
            return False
        return True
