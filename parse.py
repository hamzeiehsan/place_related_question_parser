import csv
import json
import logging
import re

import sklearn
from allennlp.modules.elmo import Elmo, batch_to_ids
from allennlp.predictors.predictor import Predictor

from ner import NER
from utils import Utils

logging.basicConfig(level=logging.DEBUG)


class Node:
    def __init__(self, parent, mapping, sentence):
        self.parent = parent
        self.nodeType = str(mapping['nodeType'])
        self.word = str(mapping['word'])
        self.attributes = mapping['attributes']
        self.link = mapping['link']
        self.children = []
        self.is_fuzzy_matched = False
        self.fuzzy_word = ''
        self.role = ''
        if parent is None:
            self.index = 10000
        else:
            self.index = parent.index + parent.word.index(self.word) * 10
        if 'children' in mapping:
            raw_children = mapping['children']
            for raw_child in raw_children:
                child = Node(self, raw_child, sentence)
                self.children.append(child)
        self.is_a_leaf = len(self.children) == 0

    def is_it_a_leaf(self):
        return self.is_a_leaf

    def get_children(self):
        return self.children

    def get_node_type(self):
        return self.nodeType

    def get_word(self):
        return self.word

    def get_parent(self):
        return self.parent

    def is_a_stop_word(self):
        return self.word.lower().strip() in Utils.stop_words

    def is_a_noun(self):
        if self.is_a_stop_word():
            return False
        if self.nodeType.startswith("N"):
            return True
        return False

    def is_a_verb(self):
        if self.is_a_stop_word():
            return False
        if self.nodeType.startswith("VB") and ' ' not in self.word:
            return True
        return False

    def is_unknown(self):
        return self.role == ''

    def is_a_wh(self):
        if self.nodeType.startswith("WH") and self.word.strip() != 'that':
            return True
        return False

    def is_a_pp(self):
        if self.nodeType.startswith("PP"):
            return True
        return False

    def is_a_in(self):
        if self.nodeType.startswith("IN"):
            return True
        return False

    def is_a_adj(self):
        if self.nodeType.startswith("JJ") or self.nodeType.startswith("ADJ") or self.nodeType.startswith("CD"):  # new adj tag (CD) added
            return True
        return False

    def get_leaves(self):
        leaves = []
        if self.is_a_leaf:
            leaves.append(self)
        else:
            for child in self.children:
                c_leaves = child.get_leaves()
                if c_leaves is not None:
                    leaves.extend(c_leaves)
        return leaves

    def is_your_child(self, node):
        if node.word in self.word:
            if self.__eq__(node):
                return True
            else:
                for child in self.children:
                    res = child.is_your_child(node)
                    if res:
                        return True
        return False

    def get_siblings(self):
        siblings = []
        if self.parent is None:
            return siblings
        for child in self.parent.children:
            if not child == self:
                siblings.append(child)
        return siblings

    def analyze(self):
        logging.debug('analyzing node called {}'.format(self.__repr__()))
        cond = False
        if self.is_a_noun():
            logging.debug('noun phrase has been found {}'.format(self.word))
        elif self.is_a_verb():
            logging.debug('verb phrase has been found {}'.format(self.word))
        if cond:
            return True
        for child in self.children:
            child.analyze()
        return True

    def find_fuzzy(self, string):
        nodes = []
        if self.word.strip().lower().startswith(string.strip().lower()) or self.word.strip().lower().startswith('the '+string.strip().lower()):
            self.is_fuzzy_matched = True
            self.fuzzy_word = string
            nodes.append(self)
        for child in self.children:
            res = child.find_fuzzy(string)
            if res is not None and len(res) > 0:
                nodes.extend(res)
        return nodes

    def set_role(self, string, role):
        if self.word.strip().lower() == string.strip().lower() or\
                self.word.strip().lower() == 'the ' + string.strip().lower():
            self.role = role
            return True
        for child in self.children:
            child.set_role(string, role)
        return False

    def find(self, string):
        nodes = []
        if self.word.strip().lower() == string.strip().lower() or self.word.strip().lower() == 'the ' + string.strip().lower():
            nodes.append(self)
        for child in self.children:
            res = child.find(string)
            if res is not None:
                nodes.extend(res)
        return nodes

    def iterate(self):
        logging.debug('word: {} and type: {}'.format(self.word, self.nodeType))
        for child in self.children:
            child.iterate()

    def is_it_ok_for_intent(self, str_sentence, str_intent):
        try:
            i_index = str_sentence.index(str_intent)
            b_index = str_sentence.replace(',', '').index(self.word.replace(',', '').replace('  ', ' '))
            if b_index < i_index:
                return False
        except:
            logging.info('wait here, '+str_sentence+' :: '+self.word)
        val = True
        if self.role == 'n' or self.role == 'r' or self.role == 'd' or self.role == 'a' or self.role == 's':
            val = False
            return val
        elif self.role == '' and len(self.children) == 0:
            return val
        for child in self.children:
            val = val and child.is_it_ok_for_intent(str_sentence, str_intent)
        return val

    def resolve_intent(self, str_sentence, str_intent):
        intent = ''

        if self.is_a_noun():
            if self.role == '' or self.role == 't' or self.role == 'o':
                if self.is_it_ok_for_intent(str_sentence, str_intent):
                    return self
        for child in self.children:
            c_intent = child.resolve_intent(str_sentence, str_intent)
            if c_intent is not None:
                return c_intent
        return None

    def get_resolve_list(self):
        list_nodes = []
        if self.role == '':
            if len(self.children) > 0:
                for child in self.children:
                    list_nodes.extend(child.get_resolve_list())
            else:
                list_nodes.append(self)
                return list_nodes
        else:
            list_nodes.append(self)
        return list_nodes

    def iterate_nouns(self):
        nouns = []
        if self.is_a_noun():
            logging.debug('noun is: {}'.format(self.word))
            nouns.append(self)
        for child in self.children:
            nouns.extend(child.iterate_nouns())
        return nouns

    def iterate_verbs(self):
        verbs = []
        if self.is_a_verb():
            logging.debug('verb is: {}'.format(self.word))
            verbs.append(self)
        for child in self.children:
            verbs.extend(child.iterate_verbs())
        return verbs

    def iterate_adjectives(self):
        adjs = []
        if self.is_a_adj():
            logging.debug('adjective: {}'.format(self.word))
            adjs.append(self)
        if not self.nodeType.startswith("ADJ"):
            for child in self.children:
                adjs.extend(child.iterate_adjectives())
        return adjs

    def iterate_pps(self):
        pps = []
        if self.is_a_pp():
            logging.debug('pp is: {}'.format(self.word))
            pps.append(self)
        for child in self.children:
            pps.extend(child.iterate_pps())
        return pps

    def get_in_in_pp(self):
        if self.is_a_in():
            logging.debug('IN found: {}'.format(self.word))
            return self
        for child in self.children:
            return child.get_in_in_pp()

    def iterate_wh(self):
        whs = []
        if self.is_a_wh():
            logging.debug('wh found, {}'.format(self.word))

            whs.append(self)
            return whs
        else:
            for child in self.children:
                whs.extend(child.iterate_wh())
        return whs

    def __repr__(self):
        representation = ""
        representation += str(self.nodeType) + "{" + self.role + "}"
        if len(self.children) > 0:
            representation += "("
            for child in self.children:
                representation += child.__repr__()
                representation += ", "
            representation = representation[:-2]
            representation += ")"

        return representation

    def __eq__(self, other):
        """Overrides the default implementation"""
        if isinstance(other, Node):
            return self.word == other.word and self.index == other.index
        return False

    def __hash__(self):
        return hash(self.index) + hash(self.word)


# parse tree is a class that capture root node and enable us to iterate over the nodes...


class ParseTree:
    def __init__(self, root, sentence):
        self.root = Node(None, root, sentence)

    def get_root(self):
        return self.root

    def get_type(self):
        return self.root.get_node_type()

    def analyze(self):
        self.root.analyze()

    def get_intent(self):
        return self.root.iterate_wh()

    def resolve_intent(self, sentence, intent):
        return self.root.resolve_intent(sentence, intent)

    def find(self, string):
        nodes = self.root.find(string) #simple find
        if nodes is None or len(nodes) == 0:
            fuzzy_result = self.root.find_fuzzy(string) #fuzzy start search --> find
            if (fuzzy_result is None or len(fuzzy_result) == 0) and ' ' in string:
                fuzzy_result = self.find(string.split()[0]) #complex word division --> find
                if fuzzy_result is not None and len(fuzzy_result) == 1:
                    fuzzy_node = fuzzy_result[0]
                    fuzzy_node.is_fuzzy_matched = True
                    fuzzy_node.fuzzy_word = string
                    return [fuzzy_node]
                return fuzzy_result
            return fuzzy_result
        return nodes

    def set_role(self, string, role):
        return self.root.set_role(string, role)

    def get_leaves(self):
        return self.root.get_leaves()

    def iterate(self):
        logging.info('iterating and printing roles')
        self.root.iterate()
        logging.info('iterating nouns: ')
        self.root.iterate_nouns()
        logging.info('iterating verbs: ')
        self.root.iterate_verbs()

    def get_nouns(self):
        return self.root.iterate_nouns()

    def get_verbs(self):
        return self.root.iterate_verbs()

    def get_pps(self):
        return self.root.iterate_pps()

    def get_adjectives(self):
        return self.root.iterate_adjectives()

    def __repr__(self):
        return self.root.__repr__()


def is_inside(string, list):
    for l in list:
        if string in l or l in string:
            return True
    return False


def is_left_inside(string, list):
    for l in list:
        if string.lower().strip() == l.lower().strip():
            return True
    return False


class GeoAnalyticalQuestion:
    def __init__(self, id, source, year, title, question,
                 q_type):  # change the source and add taxonomy! also put it result
        self.id = id
        self.source = source
        self.q_type = q_type
        self.year = year
        self.question = question.replace('\'s', '').replace('-', '')
        self.title = title
        self.parser = ''
        self.sentence = Sentence(self.question, self.source, self.q_type)

    def analyze(self):
        self.parser = self.sentence.analyze()
        return self.parser


class Sentence():
    def __init__(self, sentence, source, s_type):
        self.sentence = sentence
        self.source = source
        self.s_type = s_type
        self.parse_tree = None

    @staticmethod
    def is_ambiguous(intent_list, intent_code):
        if len(intent_list) == 1 and ('o' not in intent_code or 't' not in intent_code):
            if intent_code == '8':
                return False
            else:
                return True
        return False

    @staticmethod
    # old working code
    # def resolving_intent(desc_list_info):
    def resolving_intent(tree, sentence, intent):
        flag = False
        val = ''
        resolved_intent_list = []
        resolved_intent_code = ''
        res = tree.resolve_intent(sentence, intent)
        if res is not None:
            list_nodes = res.get_resolve_list()
            for l in list_nodes:
                resolved_intent_list.append({'tag': l.role, 'value': l.word})
                resolved_intent_code += l.role
        result = {'list': resolved_intent_list, 'code': resolved_intent_code}
        return result

    @staticmethod
    def resolve_intent(tree):
        return tree.resolve_intent()

    def analyze(self):
        logging.info('*******************************************************')
        result_dict = {}
        result_dict['source'] = self.source.strip().lower()
        result_dict['q_type'] = self.s_type.strip().lower()
        res = model.predict(sentence=self.sentence)
        root_dict = res['hierplane_tree']['root']
        logging.info('sentence {} parsed as {}'.format(self.sentence, root_dict))

        emb = elmo(batch_to_ids([self.sentence.split()]))['elmo_representations'][0].detach().numpy()

        parse_tree = ParseTree(root_dict, self.sentence)
        # logging.info('ParseTree type is: {}'.format(parse_tree.get_type()))
        # parse_tree.iterate()
        logging.info('Now it\'s time to check the string representation \n{}'.format(str(parse_tree.root)))
        # parse_tree.analyze()
        logging.info('extracting information')
        all_nodes = set()
        all_intent_nodes = set()
        all_desc_nodes = set()
        toponyms = NER.extract_place_names(self.sentence)

        topo_nodes = set()
        for t in toponyms:
            logging.debug('\ttoponym:\t{}'.format(t))
            nodes = parse_tree.find(t)
            if nodes is None:
                logging.error('An error in finding nodes')
            else:
                for n in nodes:
                    n.role = 'n'
                    parse_tree.set_role(n.word, 'n')
                    topo_nodes.add(n)
        for t_node in topo_nodes:
            logging.debug('\t**Found Node: {} and index {}'.format(t_node.word, t_node.index))

        dates = NER.extract_dates(self.sentence)
        dates_nodes = set()
        for d in dates:
            logging.debug('\tdate:\t{}'.format(d))
            nodes = parse_tree.find(d)
            if nodes is None:
                logging.error('An error in finding nodes')
            else:
                for n in nodes:
                    n.role = 'd'
                    parse_tree.set_role(n.word, 'd')
                    dates_nodes.add(n)

        for d_node in dates_nodes:
            logging.debug('\t**Found Node: {} and index {}'.format(d_node.word, d_node.index))
        all_nodes = all_nodes.union(dates_nodes)
        all_desc_nodes = all_desc_nodes.union(dates_nodes)

        whs_nodes = parse_tree.get_intent()
        whs = []
        for wh_node in whs_nodes:
            wh_node.role = intent_encoding(wh_node, PRONOUN)
            parse_tree.set_role(wh_node.word, wh_node.role)
            whs.append(wh_node.word)

        if whs is None or len(whs) == 0:
            if parse_tree.root.word.lower().strip().split()[0] in CONDITIONAL:
                wh_node = parse_tree.find(parse_tree.root.word.split()[0])
                if wh_node is not None and len(wh_node) > 0:
                    wh_node[0].role = '8'
                    parse_tree.set_role(wh_node[0].word, '8')
                    whs_nodes.append(wh_node[0])
        for w in whs:
            logging.info('intent is: {}'.format(w))
        all_nodes = all_nodes.union(whs_nodes)
        all_intent_nodes = all_intent_nodes.union(whs_nodes)
        result_dict['intents'] = whs
        a_entities_set = set()
        a_entities_nodes = set()
        a_types = []
        a_types_nodes = set()
        for whs_node in whs_nodes:
            wh_nouns = whs_node.iterate_nouns()
            wh_nouns.sort(key=sort_function, reverse=True)
            for n in wh_nouns:
                if not is_inside(n.word, toponyms) and not is_inside(n.word, dates) and not is_left_inside(
                        n.word, a_types) and is_a_new_one(a_types_nodes, n):
                    if is_left_inside(n.word.lower().strip(), pt_set) or is_left_inside(n.word.lower().strip(),
                                                                                        pt_dict.keys()):
                        a_types.append(n.word)
                        n.role = 't'
                        parse_tree.set_role(n.word, n.role)
                        a_types_nodes.add(n)
                    elif ' ' not in n.word.strip() and len(n.word) > 2:
                        if n.word.strip().lower() in countries:
                            topo_nodes.add(n)
                            n.role = 'n'
                            parse_tree.set_role(n.word, n.role)
                            toponyms.append(n.word)
                        else:
                            a_entities_set.add(n.word)
                            n.role = 'o'
                            parse_tree.set_role(n.word, n.role)
                            a_entities_nodes.add(n)
        for t in a_types:
            logging.debug('\ttype in intent:\t{}'.format(t))
        a_entities = list(a_entities_set)
        for e in a_entities:
            logging.debug('\tentity in intent:\t{}'.format(e))
        all_nodes = all_nodes.union(a_types_nodes)
        all_intent_nodes = all_intent_nodes.union(a_types_nodes)
        all_nodes = all_nodes.union(a_entities_nodes)
        all_intent_nodes = all_intent_nodes.union(a_entities_nodes)

        nouns = parse_tree.get_nouns()
        nouns.sort(key=sort_function, reverse=True)
        types = []
        types_nodes = set()
        entities_set = set()
        entities_nodes = set()
        for n in nouns:
            if not is_inside(n.word, toponyms) and not is_inside(n.word, dates) and not is_inside(
                    n.word, whs) and not is_left_inside(n.word, types) and is_a_new_one(types_nodes, n):
                if is_left_inside(n.word.lower().strip(), pt_set) or is_left_inside(n.word.lower().strip(),
                                                                                    pt_dict.keys()):
                    types.append(n.word)
                    n.role = 't'
                    parse_tree.set_role(n.word, n.role)
                    types_nodes.add(n)
                elif ' ' not in n.word.strip() and len(n.word) >= 2:
                    if n.word.strip().lower() in countries:
                        topo_nodes.add(n)
                        n.role = 'n'
                        parse_tree.set_role(n.word, n.role)
                        toponyms.append(n.word)
                    else:
                        entities_set.add(n.word)
                        n.role = 'o'
                        parse_tree.set_role(n.word, n.role)
                        entities_nodes.add(n)
        for t in types:
            logging.debug('\ttype:\t{}'.format(t))
        entities = list(entities_set)
        for e in entities:
            logging.debug('\tentity:\t{}'.format(e))
        all_nodes = all_nodes.union(types_nodes)
        all_desc_nodes = all_desc_nodes.union(types_nodes)
        all_nodes = all_nodes.union(entities_nodes)
        all_desc_nodes = all_desc_nodes.union(entities_nodes)

        verbs = parse_tree.get_verbs()
        situations = []
        situations_nodes = set()
        activities = []
        activities_nodes = set()
        unknowns = []
        unknowns_nodes = set()
        for v in verbs:
            if v.word in self.sentence.split():
                v_index = self.sentence.split().index(v.word)
                v_emb = [emb[0][v_index]]
                logging.debug('verb is {} and len of emb is {}'.format(v.word, len(v_emb)))
                decision = verb_encoding(v_emb, actv_emb, stav_emb)
                if decision == "a":
                    activities.append(v.word)
                    v.role = 'a'
                    parse_tree.set_role(n.word, n.role)
                    activities_nodes.add(v)
                elif decision == "s":
                    situations.append(v.word)
                    v.role = 's'
                    parse_tree.set_role(n.word, n.role)
                    situations_nodes.add(v)
                else:
                    unknowns.append(v.word)
                    unknowns_nodes.add(v)
        for s in situations:
            logging.debug('\tsituation: {}'.format(s))
        for a in activities:
            logging.debug('\tactivities: {}'.format(a))
        for u in unknowns:
            logging.debug('\tunknown: {}'.format(u))
        all_nodes = all_nodes.union(activities_nodes)
        all_desc_nodes = all_desc_nodes.union(activities_nodes)
        all_nodes = all_nodes.union(situations_nodes)
        all_desc_nodes = all_desc_nodes.union(situations_nodes)

        pps = parse_tree.get_pps()
        relations = []
        relation_nodes = set()
        for pp in pps:
            for n in toponyms:
                if 'with' in pp.word.lower():
                    is_within = is_within_phrase(pp.word)
                    if is_within is not None:
                        in_pp = pp.get_in_in_pp()
                        if in_pp is not None:
                            relations.append(in_pp.word)
                            in_pp.role = 'r'
                            parse_tree.set_role(in_pp.word, in_pp.role)
                            relation_nodes.add(in_pp)
                if n in pp.word and not is_inside_right(pp.word, entities) and not is_inside_right(pp.word, a_entities):
                    in_pp = pp.get_in_in_pp()
                    if in_pp is not None:
                        relations.append(in_pp.word)
                        in_pp.role = 'r'
                        parse_tree.set_role(in_pp.word, in_pp.role)
                        relation_nodes.add(in_pp)
                        break
            for t in types:
                if t in pp.word:
                    in_pp = pp.get_in_in_pp()
                    if in_pp is not None:
                        relations.append(in_pp.word)
                        in_pp.role = 'r'
                        parse_tree.set_role(in_pp.word, in_pp.role)
                        relation_nodes.add(in_pp)
                        break
        all_nodes = all_nodes.union(relation_nodes)
        all_desc_nodes = all_desc_nodes.union(relation_nodes)
        for relation in relations:
            logging.debug('\trelation: {}'.format(relation))

        adjs = parse_tree.get_adjectives()
        qualities = []
        qualities_nodes = set()
        object_qualities = []
        object_qualities_nodes = set()
        for adj in adjs:
            siblings = adj.get_siblings()
            for sibling in siblings:
                if is_inside(sibling.word, toponyms) or is_inside(sibling.word, types) or is_inside(sibling.word,
                                                                                                    a_types):
                    if not is_inside(adj.word, types) and not is_inside(adj.word, a_types):
                        qualities.append(adj.word)
                        adj.role = 'q'
                        parse_tree.set_role(adj.word, adj.role)
                        qualities_nodes.add(adj)
                        break
                elif is_inside(sibling.word, entities) or is_inside(sibling.word, a_entities):
                    object_qualities.append(adj.word)
                    adj.role = 'p'
                    parse_tree.set_role(adj.word, adj.role)
                    object_qualities_nodes.add(adj)
                    break
            if adj.role == '' and not is_inside(adj.word, toponyms) and not is_inside(adj.word, dates):
                object_qualities.append(adj.word)
                adj.role = 'p'
                parse_tree.set_role(adj.word, adj.role)
                object_qualities_nodes.add(adj)

        all_nodes = all_nodes.union(qualities_nodes)
        all_desc_nodes = all_desc_nodes.union(qualities_nodes)
        all_nodes = all_nodes.union(object_qualities_nodes)
        all_desc_nodes = all_desc_nodes.union(object_qualities_nodes)
        for q in qualities:
            logging.debug('\tquality: {}'.format(q))
        for oq in object_qualities:
            logging.debug('\tobject quality: {}'.format(oq))
        all_nodes = all_nodes.union(topo_nodes) # because now we use countries.txt to not make obvious mistakes...
        all_desc_nodes = all_desc_nodes.union(topo_nodes)
        # coding schema: where: 1, what: 2, which: 3, why: 4, how: 5, how+adj: 6 etc. make it complete... other:0...
        # ...activity: a, situation: s, quality: q, object_quality: p, relation: r, toponym: n, type: t, date: d
        ignored_nodes = []
        leaves = parse_tree.get_leaves()
        for leaf in leaves:
            if leaf.is_unknown():
                ignored_nodes.append(leaf)

        temp = []

        for leaf in ignored_nodes:
            for n in all_nodes:
                flag = True
                if n.is_fuzzy_matched:
                    if leaf.word in n.word:
                        flag = False
                        break
                else:
                    if n.is_your_child(leaf):
                        flag = False
                        break
            if flag:
                temp.append(leaf)
                all_nodes.add(leaf)

        all_list = list(all_nodes)
        intent_list = list(all_intent_nodes)
        description_list = list(all_desc_nodes)
        all_list.sort(key=lambda x: x.index, reverse=False)
        intent_list.sort(key=lambda x: x.index, reverse=False)
        description_list.sort(key=lambda x: x.index, reverse=False)
        intent_code = ''
        intent_info = []
        for node in intent_list:
            intent_code += node.role
            if node.is_fuzzy_matched:
                intent_info.append({'tag': node.role, 'value': node.fuzzy_word})
            else:
                intent_info.append({'tag': node.role, 'value': node.word})

        desc_code = ''
        desc_info = []
        for node in description_list:
            desc_code += node.role
            if node.is_fuzzy_matched:
                desc_info.append({'tag': node.role, 'value': node.fuzzy_word})
            else:
                desc_info.append({'tag': node.role, 'value': node.word})

        if Sentence.is_ambiguous(intent_list, intent_code):
            logging.info('the intention is ambiguous, code: {}'.format(intent_code))
            str_intent = ''
            for i in intent_list:
                str_intent+=i.word+' '
            resolved = Sentence.resolving_intent(parse_tree,self.sentence, str_intent.strip())
            result_dict['resolved_intent'] = resolved
            if resolved['code'] != '':
                intent_code += resolved['code']
                intent_info.extend(resolved['list'])
                desc_temp_list = []
                for d in desc_info:
                    if d not in resolved['list']:
                        desc_temp_list.append(d)
                    else:
                        logging.debug('found!')
                desc_code = desc_code.replace(resolved['code'], '', 1)
                desc_info = desc_temp_list
                logging.debug('updated...')

        result_dict['i_objects'] = []
        result_dict['i_ptypes'] = []
        result_dict['i_ptypes_qualities'] = []
        result_dict['i_object_qualities'] = []
        for i_element in intent_info:
            if i_element['tag'] == 't':
                result_dict['i_ptypes'].append(i_element['value'])
            elif i_element['tag'] == 'o':
                result_dict['i_objects'].append(i_element['value'])
            elif i_element['tag'] == 'p':
                result_dict['i_object_qualities'].append(i_element['value'])
            elif i_element['tag'] == 'q':
                result_dict['i_ptypes_qualities'].append(i_element['value'])

        result_dict['intent_code'] = intent_code
        result_dict['intent_info'] = intent_info
        result_dict['desc_code'] = desc_code
        result_dict['desc_info'] = desc_info
        all_code = ''
        all_info = []
        result_dict['situations'] = []
        result_dict['activities'] = []
        result_dict['pqualities'] = []
        result_dict['oqualities'] = []
        result_dict['relations'] = []
        result_dict['objects'] = []
        result_dict['ptypes'] = []
        result_dict['dates'] = []
        result_dict['pnames'] = []
        for node in all_list:
            all_code += node.role
            if node.role == '' and (is_unknown_word_in_ner_result(node.word, toponyms) or is_unknown_word_in_ner_result(node.word, dates)):
                continue
            if node.is_fuzzy_matched:
                all_info.append({'tag': node.role, 'value': node.fuzzy_word})
                result_dict = add_to_dict_list(node.role, node.fuzzy_word, result_dict)
            else:
                all_info.append({'tag': node.role, 'value': node.word})
                result_dict = add_to_dict_list(node.role, node.word, result_dict)
        result_dict['all_code'] = all_code
        result_dict['all_info'] = all_info
        logging.info('\tintent code is: {}'.format(intent_code))
        logging.info('\tdesc code is: {}'.format(desc_code))
        logging.info('\tall code is: {}'.format(all_code))
        logging.info('*******************************************************')
        self.parse_tree = parse_tree
        return result_dict


def is_unknown_word_in_ner_result(string, ner_result):
    for n in ner_result:
        if string.lower().strip() in n.lower().strip():
            return True
    return False


def add_to_dict_list(tag, value, dict):
    if value is None:
        return dict
    if tag == 'n':
        dict['pnames'].append(value)
    elif tag == 't':
        dict['ptypes'].append(value)
    elif tag == 's':
        dict['situations'].append(value)
    elif tag == 'a':
        dict['activities'].append(value)
    elif tag == 'q':
        dict['pqualities'].append(value)
    elif tag == 'p':
        dict['oqualities'].append(value)
    elif tag == 'd':
        dict['dates'].append(value)
    elif tag == 'o':
        dict['objects'].append(value)
    elif tag == 'r':
        dict['relations'].append(value)
    return dict


def is_a_new_one(list, node):
    for l in list:
        if l.is_your_child(node):
            return False
    return True


def sort_function(node):
    return len(node.word)


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


def is_inside_right(string, list):
    for l in list:
        if l in string:
            return True
    return False


def is_within_phrase(string):
    m_object = re.match(r'^[w|W]ithi?n?\s\d+[\.]?\d*\s?[\w|\W]+\Z', string + '\n')
    if m_object:
        return m_object.group()
    return None


# load word
def load_word(fword):
    words = set()
    fword = open(fword, 'r', encoding="utf8")
    for line in fword.readlines():
        word = line.strip()
        words.add(word)
    fword.close()
    return words


def list_node_to_list_word(list_node):
    list_word = []
    for n in list_node:
        list_word.append(n.word)
    return list_word


def verb_encoding(verb_emb, activity_embs, situation_embs):
    stav_similar = sklearn.metrics.pairwise.cosine_similarity(situation_embs.squeeze(), verb_emb).max()
    actv_similar = sklearn.metrics.pairwise.cosine_similarity(activity_embs.squeeze(), verb_emb).max()
    if actv_similar > max(stav_similar, 0.35):
        return "a"
    elif stav_similar > max(actv_similar, 0.35):
        return "s"
    return "u"


def intent_encoding(intent_node, pronoun_dict):
    for key, val in pronoun_dict.items():
        if key.lower().strip() in intent_node.word.lower().strip():
            return val
    if 'how' in intent_node.word.lower().strip():
        if 'JJ' in str(intent_node):
            return '6'
        else:
            return '5'
    return '0'


def read_file_geoanqu(fname):
    res = []
    with open(fname) as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')

        line_count = 0
        for row in csv_reader:
            if line_count == 0:
                logging.debug(f'Column names are {", ".join(row)}')
                line_count += 1
            else:
                geoaq = GeoAnalyticalQuestion(row[0], row[1], row[3], row[4], row[5], 'GeoAnQu')
                res.append(geoaq)
                line_count += 1
        logging.debug(f'Processed {line_count} lines.')
        return res


def read_msmarco_dataset(fname):
    res = []
    with open(fname, encoding="utf8") as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')

        line_count = 0
        for row in csv_reader:
            if line_count == 0:
                print(f'Column names are {", ".join(row)}')
                line_count += 1
            else:
                geoaq = GeoAnalyticalQuestion(row[2], '2018', 'MS MARCO',
                                              'MS MARCO v2.1 Geographic Questions', row[0], 'MS MARCO')
                res.append(geoaq)
                line_count += 1
        print(f'Processed {line_count} lines.')
        return res


def read_file_201_dataset(fname):
    res = []
    with open(fname) as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')

        line_count = 0
        for row in csv_reader:
            if line_count == 0:
                print(f'Column names are {", ".join(row)}')
                line_count += 1
            else:
                geoaq = GeoAnalyticalQuestion(line_count, '2019', 'GeoQuestion201',
                                              'Gold Standard 201 GeoQuestions', row[0], 'GeoQuestion201')
                res.append(geoaq)
                line_count += 1
        print(f'Processed {line_count} lines.')
        return res


def read_dummy_samples():
    res = []
    res.append(GeoAnalyticalQuestion(1, '2019', 'Test', 'Test', 'Is the county of Antrim bigger than the county of Armagh?', 'Test'))
    res.append(GeoAnalyticalQuestion(2, '2019', 'Test', 'Test', 'What houses are for sale and within 1km from the nearest supermarket in Utrecht?', 'Test'))
    res.append(GeoAnalyticalQuestion(3, '2019', 'Test', 'Test', 'Where are the houses for sale and built between 1990 and 2000 in Utrecht??', 'Test'))
    res.append(GeoAnalyticalQuestion(4, '2019', 'Test', 'Test', 'Where are the 5star hotels in the Happy Valley ski resort?', 'Test'))
    res.append(GeoAnalyticalQuestion(5, '2019', 'Test', 'Test', 'Where is the most popular ski piste in Happy Valley ski resort?', 'Test'))
    res.append(GeoAnalyticalQuestion(6, '2019', 'Test', 'Test', 'Where are the ski pistes in Happy Valley ski resort?', 'Test'))
    res.append(GeoAnalyticalQuestion(7, '2019', 'Test', 'Test', 'How do connectivity, directness, and topology of a network affect the risk of cyclist-vehicle collision in Vancouver, Canada', 'Test'))
    res.append(GeoAnalyticalQuestion(8, '2019', 'Test', 'Test', 'What is the relationship between the average monthly sales of the Hispanic specialty stores and the distribution of the Hispanic population in Tarrant County, Texas', 'Test'))

    return res

def analyze(questions, dataset_name):
    errors = []
    results = []
    count = 0
    for question in questions:
        # try:
        count += 1
        result = {}
        result['question'] = question.question
        result['id'] = question.id
        result['source'] = question.source
        result['title'] = question.title
        parser = question.analyze()
        result.update(parser)
        results.append(result)
        percentage = round(count / len(questions) * 100, 2)
        logging.info(
            'Processing the record number ::: {count}; Currently {percentage}% of the {dataset_name} is parsed'.format(
                count=count, percentage=percentage, dataset_name=dataset_name))
        logging.info("parse tree: " + str(question.sentence.parse_tree))
        # except:
        #     logging.error('An error occured in analyzing the following question: {}'.format(question.question))
        #     errors.append(question.question)
    with open('parsing_result/{}.json'.format(dataset_name), 'w') as outfile:
        json.dump(results, outfile)
    # with open('parsing_result/{}_error.json'.format(dataset_name), 'w') as outfile:
    #     json.dump(errors, outfile)
    logging.debug('Parsing the {} dataset is finished'.format(dataset_name))



PRONOUN = dict(
    {'where': '1', 'what': '2', 'which': '3', 'when': '4', 'why': '7'})
CONDITIONAL = ['are', 'is', 'was', 'were', 'did', 'do', 'does']
model = Predictor.from_path("https://storage.googleapis.com/allennlp-public-models/elmo-constituency-parser-2020.02.10.tar.gz")

fpt = 'data/place_type/type-set.txt'
factv = 'data/verb/action_verb.txt'
fstav = 'data/verb/stative_verb.txt'
fcountries = 'data/gazetteer/countries.txt'

pt_set, pt_dict = load_pt(fpt)
actv = load_word(factv)
stav = load_word(fstav)

countries = load_word(fcountries)

# loading ELMo pretrained word embedding model
options_file = "https://s3-us-west-2.amazonaws.com/allennlp/models/elmo/2x4096_512_2048cnn_2xhighway/elmo_2x4096_512_2048cnn_2xhighway_options.json"
weight_file = "https://s3-us-west-2.amazonaws.com/allennlp/models/elmo/2x4096_512_2048cnn_2xhighway/elmo_2x4096_512_2048cnn_2xhighway_weights.hdf5"

elmo = Elmo(options_file, weight_file, 2, dropout=0)

# Verb Elmo representation
actv_emb = elmo(batch_to_ids([[v] for v in actv]))['elmo_representations'][0].detach().numpy()
stav_emb = elmo(batch_to_ids([[v] for v in stav]))['elmo_representations'][0].detach().numpy()

logging.info('The program starts to parse test samples')
samples = read_dummy_samples()
analyze(samples, 'Samples')

# logging.info('The program starts to parse GeoAnQu...')
# geoanqu = read_file_geoanqu('data/datasets/GeoAnQu.csv')
# analyze(geoanqu, 'GeoAnQu')
#
# logging.info('The program starts to parse GeoQuestion201...')
# geoquestion201 = read_file_201_dataset('data/datasets/GeoQuestion201.csv')
# analyze(geoquestion201, 'GeoQuestion201')
#
# logging.info('The program starts to parse MS MARCO...')
# msmarco = read_msmarco_dataset('data/datasets/MS MARCO.csv')
# analyze(msmarco, 'MS MARCO')
