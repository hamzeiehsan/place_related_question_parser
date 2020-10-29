from anytree import AnyNode, RenderTree, PostOrderIter
import re

import anytree.cachedsearch as search


class PlaceQuestionParseTree:
    spatiotemporal_propositions = ['in', 'of', 'on', 'at', 'within', 'from', 'to', 'near', 'close', 'between', 'beside',
                                   'by', 'since', 'until', 'before', 'after', 'close to', 'near to', 'closest to',
                                   'nearest to']
    complex_spatial_propositions = [' within \d.* ',
                                    ' at most \d.* ',
                                    ' less than \d.* away ',
                                    ' more than \d.* away ',
                                    ' in \d.* radius ',
                                    ' in a range of \d.* ',
                                    ' in the range of \d.* ',
                                    ' north ', ' south ', ' east ', ' west ', ' part ',
                                    ' northeast ', ' southeast ', ' northwest ', ' southwest ']

    def __init__(self, parse_dict):
        self.parse_dict = parse_dict
        self.tree = None
        self.root = None
        self.construct_tree()

    def construct_tree(self):
        root = AnyNode(name=self.parse_dict['word'], nodeType=self.parse_dict['nodeType'], role='',
                       spans={'start': 0, 'end': len(self.parse_dict['word'])})
        if 'children' in self.parse_dict.keys():
            for child in self.parse_dict['children']:
                self.add_to_tree(child, root)
        self.root = root
        self.tree = RenderTree(root)

    def add_to_tree(self, node, parent):
        local_start = parent.name.find(node['word'])
        n = AnyNode(name=node['word'], nodeType=node['nodeType'], parent=parent, role='',
                    spans={'start': parent.spans['start']+local_start, 'end': parent.spans['start']+local_start+len(node['word'])})
        if 'children' in node.keys():
            for child in node['children']:
                self.add_to_tree(child, n)

    def render(self):
        self.tree = RenderTree(self.root)

    def __repr__(self):
        if self.tree is None:
            return "Empty Tree"
        res = ""
        for pre, fill, node in self.tree:
            res += "%s%s (%s) {%s}" % (pre, node.name, node.nodeType, node.role)+"\n"
        return res

    def label_tree(self):
        self.clean_tree()
        self.label_conjunctions()

        #self.label_spatiotemporal_relationships()
        #self.clean_locations()
        #self.update()

        res = self.label_non_platial_objects()
        res2 = self.label_numbers()
        self.update()
        return {**res, **res2}

    def find_node_by_exact_name(self, string):
        return search.findall_by_attr(self.root, string)

    def find_node_by_name(self, string):
        res = self.find_node_by_exact_name(string)
        if len(res) > 0:
            return res
        return search.findall(self.root, filter_=lambda node: node.name in string.split())

    def label_role(self, name, role, clean=False, question_words=False, comparison=False):
        nodes = self.find_node_by_name(name)
        if len(nodes) == 1:
            nodes[0].role = role
            if clean:
                nodes[0].children = []
            return True
        else:
            min_depth = 1000
            selected = None
            for node in nodes:
                if node.depth < min_depth and node.name not in ['of']:
                    min_depth = node.depth
                    selected = node
                else:
                    node.parent = None
                selected.name = name
                if question_words and self.root.name.startswith(name):
                    selected.nodeType = 'WH'
                elif comparison:
                    selected.nodeType = 'JJR'
                elif not question_words and not comparison:
                    selected.nodeType = 'NP'
                selected.role = role
                # if node.nodeType.startswith("N"):
                #     node.role = role
                #     if clean:
                #         node.children = []
        return False

    def clean_tree(self):
        named_objects = search.findall(self.root, filter_=lambda node: node.role in ("E", "P", "e", "p", "d", "o"))
        for named_object in named_objects:
            if len(named_object.siblings) == 1 and (named_object.siblings[0].nodeType == 'DT'):
                named_object.parent.role = named_object.role
                named_object.parent.children = []
            elif len(named_object.siblings) == 1 and named_object.siblings[0].role == named_object.role:
                named_object.parent.role = named_object.role

    def label_spatiotemporal_relationships(self):
        named_objects = search.findall(self.root, filter_=lambda node: node.role in ("P", "p", "d"))
        compound_relationships = {}
        for named_object in named_objects:
            for sibling in named_object.siblings:
                if sibling.nodeType == 'IN' and named_object.parent.nodeType in ['PP', 'VP'] and\
                        sibling.name in PlaceQuestionParseTree.spatiotemporal_propositions:
                    if named_object.role == 'd':
                        sibling.role = 'r'
                    else: # complex spatial relationship with ['of', 'from', 'to']
                        sibling.role = 'R'
                        if ' ' in sibling.name:
                            compound_relationships[sibling.name] = {'start': self.root.name.index(sibling.name),
                                                                    'end': self.root.name.index(sibling.name) + len(sibling.name)}
                        if sibling.name in ['of', 'to', 'from']:
                            for reg in PlaceQuestionParseTree.complex_spatial_propositions:
                                pattern = reg + sibling.name
                                regex_search = re.search(pattern, self.root.name)
                                if regex_search is not None:
                                    compound_relationships[self.root.name[regex_search.regs[0][0]:regex_search.regs[0][1]]]={'start': regex_search.regs[0][0], 'end': regex_search.regs[0][1]}
                                    self.label_complex_spatial_relationships(sibling, pattern)
                    named_object.parent.role = 'LOCATION'
        return compound_relationships

    def label_complex_spatial_relationships(self, prep, pattern):
        matched = False
        context = prep.parent
        text = ''
        while not matched:
            regex_search = re.search(pattern.strip(), context.name)
            if regex_search is not None:
                matched = True
                text = context.name[regex_search.regs[0][0]: regex_search.regs[0][1]]
                break
            if context.parent is None:
                break
            context = context.parent
        if matched:
            if context.name == text:
                context.role = 'R'
            else:
                nodes = PlaceQuestionParseTree.iterate_and_find(context, text)
                new_node = AnyNode(name=text, nodeType='IN', role='R')
                before = []
                after = []

                firstparent = nodes[0].parent
                if firstparent != context:
                    for child in context.children:
                        if self.root.name.index(child.name) + len(child.name) <= self.root.name.index(text):
                            before.append(child)

                for child in firstparent.children:
                    if child in nodes:
                        break
                    before.append(child)

                lastparent = prep.parent
                for child in lastparent.children:
                    if child not in nodes:
                        after.append(child)
                while lastparent != context:
                    lastparent = lastparent.parent
                    for child in lastparent.children:
                        if self.root.name.index(text)+len(text)<=self.root.name.index(child.name):
                            after.append(child)
                context.children = []
                for b in before:
                    b.parent = context

                for node in nodes:
                    node.parent = new_node

                new_node.parent = context

                for a in after:
                    a.parent = context

    @staticmethod
    def iterate_and_find(node, text):
        res = []
        for child in node.children:
            if child.name in text:
                res.append(child)
                text = text.replace(child.name, '', 1)
            elif text.strip() != '':
                res.extend(PlaceQuestionParseTree.iterate_and_find(child, text))
        return res

    def label_complex_comparison(self, reg_results, comparison, role):
        contexts = search.findall(self.root, filter_=lambda node: node.spans['start']<=reg_results.regs[0][0] and
                                 node.spans['end']>=reg_results.regs[0][1])
        context = None
        vals = comparison.split()
        max_depth = -1
        for c in contexts:
            if c.depth >= max_depth:
                context = c
                max_depth = c.depth
        first = search.findall(context, filter_=lambda node: node.name == vals[0])[0]

        if first.parent.children.index(first)+1 == len(first.parent.children):
            return
        elif first.parent.children[first.parent.children.index(first)+1].role not in ['p', 'e', 'o']:
            return

        second = search.findall(context, filter_=lambda node: node.name == vals[1])[0]
        if first.parent != second.parent:
            second.parent.name = second.parent.name.replace(second.name, '').strip()
            second.parent = None
            first.parent.name = first.parent.name + ' '+second.name
        first.name = comparison
        first.role = role

    def clean_locations(self):
        named_objects = search.findall(self.root, filter_=lambda node: node.role == 'LOCATION')
        if len(named_objects) == 2:
            if named_objects[0].depth < named_objects[1].depth:
                if self.root.name.index(named_objects[0].name) < self.root.name.index(named_objects[1].name):
                    PlaceQuestionParseTree.merge(node1=named_objects[0], node2=named_objects[1])
                else:
                    PlaceQuestionParseTree.merge(node1=named_objects[0], node2=named_objects[1], order=False)
            else:
                if self.root.name.index(named_objects[0].name) < self.root.name.index(named_objects[1].name):
                    PlaceQuestionParseTree.merge(node1=named_objects[1], node2=named_objects[0], order=False)
                else:
                    PlaceQuestionParseTree.merge(node1=named_objects[1], node2=named_objects[0])

    def clean_single_child(self):
        single_child_nodes = search.findall(self.root, filter_= lambda node: len(node.children) == 1)
        for node in single_child_nodes:
            try:
                if node.role == '':
                    node.role = node.children[0].role
                node.nodeType = node.children[0].nodeType
                children = node.children[0].children
                node.children[0].parent = None
                node.children = children
            except:
                print('error in cleaning...')

    @staticmethod
    def merge(node1, node2, order=True):
        node = None
        if order:
            node = AnyNode(name=node1.name + ' ' + node2.name, nodeType=node1.nodeType, role=node1.role)
        else:
            node = AnyNode(name=node2.name + ' ' + node1.name, nodeType=node1.nodeType, role=node1.role)
        node.parent = node1.parent
        if order:
            node1.parent = node
            node2.parent = node
        else:
            node2.parent = node
            node1.parent = node

    def update(self):
        for node in PostOrderIter(self.root):
            if len(node.children) > 0:
                name = ''
                for child in node.children:
                    name += child.name + ' '
                if node.name != name:
                    node.name = name.strip()
                if len(node.children) == 1 and (node.role == '' or node.role == node.children[0].role) and \
                        node.nodeType == node.children[0].nodeType:
                    node.role = node.children[0].role
                    node.children = node.children[0].children

    def label_non_platial_objects(self):
        npos = search.findall(self.root, filter_=lambda node: node.nodeType.startswith('N') and
                                                       node.role == '' and len(node.children) == 0)
        res = {}
        for npo in npos:
            npo.role = 'o'
            if npo.name in ['border', 'cross', 'crosses', 'borders']:
                npo.role = 's'

        for npo in npos:
            parent = npo.parent
            if parent is not None:
                all_objects = True
                for child in parent.children:
                    if child.role != 'o' and child.nodeType != 'DT' and  child.role != 'p':
                        all_objects = False
                if all_objects:
                    parent.role = 'o'
                    parent.children = []
                    res[parent.name] = {'start':self.root.name.index(parent.name), 'end':self.root.name.index(parent.name)+len(parent.name)}
        return res

    def get_verbs(self):
        verb_nodes = search.findall(self.root,
                                    filter_=lambda node: node.nodeType.startswith("VB") and ' ' not in node.name)
        verbs = []
        for node in verb_nodes:
            verbs.append(node.name)
        return verbs

    def label_situation_activities(self, verbs, decisions):
        verb_nodes = search.findall(self.root, filter_=lambda node:node.nodeType.startswith("VB") and node.name in verbs)
        for i in range(len(verbs)):
            node = verb_nodes[i]
            decision = decisions[i]
            if decision != 'u':
                node.role = decision
            else:
                print("this verb is suspicious: " + str(node.name))
        situations = search.findall(self.root, filter_=lambda  node: node.role == 's')
        for situation in situations:
            for sibiling in situation.siblings:
                if sibiling.role == '' and sibiling.nodeType == 'PP':
                    if len(search.findall(sibiling, filter_=lambda node: node.role in ('e', 'o', 'E'))) > 0:
                        sibiling.role = 's'

        activities = search.findall(self.root, filter_=lambda node: node.role == 'a')
        for activity in activities:
            for sibiling in activity.siblings:
                if sibiling.role == '' and sibiling.nodeType == 'PP':
                    if len(search.findall(sibiling, filter_=lambda node: node.role in ('o'))) > 0:
                        sibiling.role = 'a'

    def label_events_actions(self):
        nodes = search.findall(self.root, filter_=lambda node:node.nodeType.startswith("V") and 'P' in node.nodeType and
                        node.role == '')
        for node in nodes:
            actions = 0
            events = 0
            for child in node.children:
                if child.role == 'a':
                    actions += 1
                if child.role == 'e' or child.role == 'E':
                    events += 1
            if events > 0 and actions == 0:
                node.role = 'EVENT'
            elif actions > 0 and events == 0:
                node.role = 'ACTION'

    def label_numeric_values(self):
        nodes = search.findall(self.root, filter_=lambda node: node.nodeType == 'CD' and node.role == '' and
                               len(node.children) == 0)
        for node in nodes:
            node.role = 'n'

    def label_conjunctions(self):
        nodes = search.findall(self.root, filter_=lambda node: node.nodeType in ('CC', 'IN', 'SCONJ', 'CCONJ')
                                                               and node.role == '' and len(node.children) == 0)
        for node in nodes:
            if node.name in ['and', 'both']:
                node.role = '&'
            elif node.name in ['or', 'whether']:
                node.role = '|'
            elif node.name in ['not', 'neither', 'nor', 'but', 'except']:
                node.role = '!'

            siblings = search.findall(node.parent, filter_=lambda node: node.role not in ('&', '|', '!', 'q') and
                                      node.nodeType != 'DT' and (node.role != '' or node.nodeType == ','))
            sibling_roles = set()
            for sibling in siblings:
                if sibling.nodeType == ',':
                    sibling.role = node.role
                else:
                    sibling_roles.add(sibling.role)
            if len(sibling_roles) == 1:
                node.parent.role = list(sibling_roles)[0]
        self.update()

    def label_numbers(self):
        numbers = search.findall(self.root, filter_= lambda node: node.role == '' and node.nodeType == 'CD')
        units = {}
        for num in numbers:
            num.role = 'n'
            check = False
            added = False
            for sibling in num.parent.children:
                if sibling == num:
                    check = True
                elif check and sibling.name in PlaceDependencyTree.UNITS:
                    if num.parent.role == '':
                        num.parent.role = 'MEASURE'
                    if num.name+' '+sibling.name in self.root.name:
                        units[num.name+' '+sibling.name] = {'start':self.root.name.index(num.name+' '+sibling.name),
                                                            'end': self.root.name.index(num.name+' '+sibling.name )+len(num.name+' '+sibling.name )}
                        added = True
            if not added and num.parent.nodeType == 'QP' and num.parent.parent is not None:
                found = False
                for child in num.parent.parent.children:
                    if child == num.parent:
                        found = True
                    elif found and child.name in PlaceDependencyTree.UNITS:
                        new_node = AnyNode(child.parent, role='MESAURE', name=num.name + ' ' + child.name, nodeType='NP')
                        num.parent = new_node
                        child.parent = new_node
                        units[new_node.name] = {'start': self.root.name.index(new_node.name),
                                                'end': self.root.name.index(new_node.name) + len(new_node.name)}
        return units

    def label_qualities(self):
        compounds = []
        adjectives = search.findall(self.root, filter_= lambda node: node.nodeType.startswith('AD'))
        for adj in adjectives:
            if len(search.findall(adj, filter_= lambda node: node.nodeType in ['CC', 'NP', 'NNS', 'NN'])) == 0:
                res = PlaceQuestionParseTree.label_adjective_roles(adj)
                compounds.extend(res)
        other_adjectives = search.findall(self.root, filter_= lambda node: node.nodeType.startswith('J') and node.parent.role == '')
        for adj in other_adjectives:
            res = PlaceQuestionParseTree.label_adjective_roles(adj)
            compounds.extend(res)
        return compounds

    @staticmethod
    def label_adjective_roles(adj):
        compounds = []
        found = False
        for child in adj.parent.children:
            if child == adj:
                found = True
            elif found and child.nodeType.startswith('N'):
                if child.role in ['o', 'e', 'E']:
                    adj.role = 'q'
                elif child.role in ['p', 'P']:
                    adj.role = 'Q'
                else:
                    print('unresolved adjective! ' + adj.name + ' ' + child.name)
                if ' ' in adj.name:
                    compounds.append(adj.name)
                break
            elif found and child.nodeType in['PP', 'IN']:
                if child.nodeType == 'IN':
                    adj.parent = None
                    child.name = adj.name+' '+child.name
                    compounds.append(child.name)
                elif child.nodeType == 'PP' and child.children[0].nodeType == 'IN':
                    if len(adj.parent.children) == 2:
                        child.parent = adj.parent
                        child.name = adj.name + ' '+ child.name
                        adj.parent = None
                        child.children[0].name = adj.name+' '+child.children[0].name
                        compounds.append(child.children[0].name)
                    else:
                        adj.parent = None
                        child.children[0].name = adj.name + ' ' + child.children[0].name
                        compounds.append(child.children[0].name)
                else:
                    print('unresolved adjective '+ adj.name + ' ' + child.name)
        return compounds

    @staticmethod
    def context_builder(list_str, node):
        boolean_var = True
        for string in list_str:
            boolean_var = boolean_var and string in node.name  # multi-word?
        return boolean_var

    def search_context(self, list_str):
        nodes = search.findall(self.root, filter_=lambda node: PlaceQuestionParseTree.context_builder(list_str, node))
        max_depth = -1
        selected = None
        for node in nodes:
            if node.depth > max_depth:
                max_depth = node.depth
                selected = node
        return selected

    def apply_dependencies(self, dependencies):
        verb_deps = []
        cc_deps = []
        adj_noun_deps = []
        complex_prep = []
        comparisons = []
        units = []
        for dependency in dependencies:
            if dependency.relation.link == 'HAS/RELATE' and 'VERB' in dependency.arg1.attributes and (
                    'NOUN' in dependency.arg2.attributes or 'PROPN' in dependency.arg2.attributes):
                verb_deps.append(dependency)
            elif dependency.relation.link == 'IS/ARE' and dependency.relation.name == 'ADJ':
                adj_noun_deps.append(dependency)
            elif dependency.relation.link == 'IS/ARE' and dependency.relation.name == 'PRP':
                complex_prep.append(dependency)
            elif dependency.relation.name == 'UNIT':
                units.append(dependency)
            elif dependency.relation.attributes is not None:
                if 'CCONJ' in dependency.relation.attributes or 'SCONJ' in dependency.relation.attributes:
                    cc_deps.append(dependency)
                elif dependency.relation.name != 'RELATION' and 'ADJ' in dependency.relation.attributes:
                    comparisons.append(dependency)
        print('Complex Prepositions:')
        self.apply_complex_relationships_dependencies(complex_prep)
        print('Verb-Noun Relationships:')
        self.apply_verb_noun_dependencies(verb_deps)
        print('Conjunctions:')
        self.apply_conjunction_dependencies(cc_deps)
        print('Adjective-Noun Relationships:')
        self.apply_adj_noun_dependencies(adj_noun_deps)
        print('Comparisons:')
        self.apply_comparison_dependencies(comparisons)
        print('Units:')
        self.apply_unit_dependencies(units)

    def apply_verb_noun_dependencies(self, dependencies):
        for dep in dependencies:
            str_list = [dep.arg1.name, dep.arg2.name]
            context = self.search_context(str_list)
            print(context)

    def apply_complex_relationships_dependencies(self, dependencies):
        for dep in dependencies:
            str_list = [dep.arg1.name, dep.arg2.name]
            context = self.search_context(str_list)
            print(context)

    def apply_conjunction_dependencies(self, dependencies):
        for dep in dependencies:
            str_list = [dep.relation.name, dep.arg1.name, dep.arg2.name]
            context = self.search_context(str_list)
            print(context)

    def apply_adj_noun_dependencies(self, dependencies):
        for dep in dependencies:
            str_list = [dep.arg1.name, dep.arg2.name]
            context = self.search_context(str_list)
            print(context)

    def apply_unit_dependencies(self, dependencies):
        for dep in dependencies:
            str_list = [dep.arg1.name, dep.arg2.name]
            context = self.search_context(str_list)
            print(context)

    def apply_comparison_dependencies(self, dependencies):
        for dep in dependencies:
            str_list = [dep.relation.name, dep.arg1.name, dep.arg2.name]
            context = self.search_context(str_list)
            firsts = search.findall(context, filter_=lambda node: dep.arg1.name in node.name and node != context)
            seconds = search.findall(context, filter_=lambda node: dep.arg2.name in node.name and node != context)
            first = PlaceQuestionParseTree.valid_node_selection(firsts, ['NN', 'NNS', 'NP', 'NPS'],
                                                                ['VB', 'VP', 'VBZ'])
            second = PlaceQuestionParseTree.valid_node_selection(seconds, ['NN', 'NNS', 'NP', 'NPS'],
                                                                 ['VB', 'VP', 'VBZ'])
            relation = PlaceQuestionParseTree.find_exact_match(context, dep.relation.name)
            print(first)
            print(second)
            print(relation)
            first.parent = relation
            second.parent = relation
            relation.role = 'COMPARISON'
            relation.parent.children = [relation]
            relation.parent.name = ' '.join([first.name, relation.name, second.name])
            self.clean_tree()

    @staticmethod
    def valid_node_selection(nodes, valid_pos_tags, invalid_tags):
        if len(nodes) == 1:
            return nodes[0]
        max_depth = -1
        selected = None
        for node in nodes:
            invalid_child = search.findall(node, filter_=lambda child: child != node and child.nodeType in invalid_tags)
            if len(invalid_child) == 0 and node.nodeType in valid_pos_tags and max_depth < node.depth:
                max_depth = node.depth
                selected = node
        return selected

    @staticmethod
    def find_exact_match(context, name):
        matches = search.findall(context, filter_=lambda node: node.name == name)
        max_depth = 1000
        selected = None
        for match in matches:
            if max_depth > match.depth:
                max_depth = match.depth
                selected = match
        selected.children = []
        return selected


class Dependency:
    def __init__(self, node1, relation, node2=None):
        self.arg1 = node1
        self.relation = relation
        self.arg2 = node2

    def is_binary(self):
        if self.arg2 is None:
            return False
        return True

    def __repr__(self):
        string = str(self.relation)+':\n\t'+str(self.arg1)
        if self.is_binary():
            string += '\n\t'+str(self.arg2)
        return string


class PlaceDependencyTree:
    UNITS = ['meters', 'kilometers', 'miles', 'mile', 'meter', 'kilometer',
     'km', 'm', 'mi', 'yard', 'hectare']
    def __init__(self, dependency_dict):
        self.dict = dependency_dict
        self.root = None
        self.tree = None
        self.construct_dependencies()
        self.dependencies = []

    def construct_dependencies(self):
        root = AnyNode(name=self.dict['word'], nodeType=self.dict['nodeType'],
                       attributes=self.dict['attributes'], spans=self.dict['spans'], link=self.dict['link'])
        if 'children' in self.dict.keys():
            for child in self.dict['children']:
                self.add_to_tree(child, root)
        self.root = root
        self.tree = RenderTree(root)

    def add_to_tree(self, node, parent):
        n = AnyNode(name=node['word'], nodeType=node['nodeType'], parent=parent,
                    attributes=node['attributes'], spans=node['spans'],
                    link=node['link'])
        if 'children' in node.keys():
            for child in node['children']:
                self.add_to_tree(child, n)

    def render(self):
        self.tree = RenderTree(self.root)

    def __repr__(self):
        if self.tree is None:
            return "Empty Tree"
        res = ""
        for pre, fill, node in self.tree:
            res+="%s%s (%s) {%s}" % (pre, node.name, node.nodeType, node.attributes)+"\n"
        return res

    def detect_dependencies(self):
        if self.tree is not None:
            self.detect_conjunctions()
            self.detect_adjectives()
            self.detect_verb_noun_relationships()
            self.detect_complex_prepositions()
            self.detect_units()

    def clean_d_tree(self, str_dict):
        for k, v in str_dict.items():
            nodes = search.findall(self.root, filter_=lambda node: node.spans[0]['start'] >= v['start'] and
            node.spans[0]['end'] <= v['end']+3 and node.name in k)
            selected = None
            depth = 1000
            for node in nodes:
                if depth > node.depth:
                    selected = node
                    depth = node.depth
            children = []
            if selected is not None:
                for node in nodes:
                    if node != selected:
                        node.parent = None
                        for child in node.children:
                            children.append(child)
                selected.name = k
            for child in children:
                if child.parent is not None:
                    child.parent = selected


    def detect_conjunctions(self):
        conjunctions = search.findall(self.root, filter_=lambda node: ('SCONJ' in node.attributes or 'CCONJ' in node.attributes)
                                                                      and node.nodeType in ['punct', 'dep', 'prep'])
        for conj in conjunctions:
            is_cc = 'CCONJ' in conj.attributes
            relation = PlaceDependencyTree.clone_node_without_children(conj)
            first = None
            if 'AUX' in conj.parent.attributes or 'VERB' in conj.parent.attributes:
                temp = search.findall(conj.parent, filter_=lambda node: node.parent == conj.parent and node.link == 'nsubj')
                print(temp)
                if len(temp) == 1:
                    first = PlaceDependencyTree.clone_node_without_children(temp[0])
            else:
                first = PlaceDependencyTree.clone_node_without_children(conj.parent)
            if is_cc:
                pairs = search.findall(conj.parent, filter_= lambda node: node.parent == conj.parent and
                               conj.parent.attributes[0] in node.attributes and node.link == 'dep')
                for pair in pairs:
                    if first is not None:
                        second = PlaceDependencyTree.clone_node_without_children(pair)
                        dep = Dependency(first, relation, second)
                        self.dependencies.append(dep)
            else:
                nodes = search.findall(conj, filter_=lambda node: node.link in ['dep', 'pobj'] and
                                                           ('PROPN' in node.attributes or 'NOUN' in node.attributes))
                for node in nodes:
                    if first is not None:
                        second = PlaceDependencyTree.clone_node_without_children(node)
                        dep = Dependency(first, relation, second)
                        self.dependencies.append(dep)

        excepts = search.findall(self.root, filter_=lambda node: node.nodeType == 'case' and 'ADP' in node.attributes)
        for ex in excepts:
            if ex.name in ['except', 'excluding']:
                override = {'nodeType':'cc', 'attributes': ['SCONJ'], 'link':'conj'}
                relation = PlaceDependencyTree.clone_node_without_children(ex, override)
                first = PlaceDependencyTree.clone_node_without_children(ex.parent)
                dep = Dependency(first, relation)
                self.dependencies.append(dep)

    def detect_adjectives(self):
        adjectives = search.findall(self.root, filter_=lambda node: 'ADJ' in node.attributes and
                                                                    node.link in ['amod', 'case', 'dep', 'pobj', 'root'])
        for adj in adjectives:
            num_comparisons = search.findall(adj, filter_=lambda node: 'NUM' in node.attributes and
                                                                       (node.parent == adj or node.parent.link in ['pobj', 'prep', 'dep']) )
            noun_comparisons = search.findall(adj, filter_=lambda
                node: ('PROPN' in node.attributes or 'NOUN' in node.attributes) and node.link == 'dep' and
                      (node.parent == adj or node.parent.link in ['prep']))
            if len(num_comparisons) > 0: # value comparison
                for d in num_comparisons:
                    parent = PlaceDependencyTree.find_first_parent_based_on_attribute(adj, ['NOUN', 'PROPN'])
                    if parent is not None:
                        first = PlaceDependencyTree.clone_node_without_children(parent)
                        relation = PlaceDependencyTree.clone_node_without_children(adj)
                        second = PlaceDependencyTree.clone_node_without_children(d)
                        dep = Dependency(first, relation, second)
                        self.dependencies.append(dep)
                    children = search.findall(d.parent, filter_=lambda node: node.link in ['dep', 'pobj'] and
                                                                      node.name in PlaceDependencyTree.UNITS)
                    for child in children:
                        first = PlaceDependencyTree.clone_node_without_children(d)
                        second = PlaceDependencyTree.clone_node_without_children(child)
                        relation = AnyNode(name='UNIT', spans=[{}], attributes=None, link='IS/ARE', nodeType='RELATION')
                        dep = Dependency(first, relation, second)
                        self.dependencies.append(dep)

            elif len(noun_comparisons) > 0 and adj.parent is not None: # noun comparison
                for n in noun_comparisons:
                    first = PlaceDependencyTree.clone_node_without_children(adj.parent)
                    relation = PlaceDependencyTree.clone_node_without_children(adj)
                    second = PlaceDependencyTree.clone_node_without_children(n)
                    dep = Dependency(first, relation, second)
                    self.dependencies.append(dep)
            else:
                relation = AnyNode(name='ADJ', spans=[{}], attributes=None, link='IS/ARE', nodeType='RELATION')
                dependency = None
                if adj.parent is not None:
                    dependency = search.findall(adj.parent, filter_=lambda node: (node.parent == adj.parent or node == adj.parent
                                                                              or adj in node.ancestors)
                                            and node.attributes[0] in ['NOUN', 'PROPN'])
                else:
                    dependency = search.findall(adj, filter_=lambda node: node.attributes[0] in ['NOUN', 'PROPN'] and node.parent == adj)
                if len(dependency) == 1:
                    first = PlaceDependencyTree.clone_node_without_children(dependency[0])
                    dep = Dependency(first, relation, adj)
                    self.dependencies.append(dep)
                else:
                    print('error -- adjective with multiple deps '+str(adj))

            adverbs = search.findall(adj, filter_=lambda node: node.link in ['advmod', 'dep'] and
                                                               node.parent == adj and 'ADV' in node.attributes)
            if len(adverbs) > 0:
                for adv in adverbs:
                    first = PlaceDependencyTree.clone_node_without_children(adj)
                    second = PlaceDependencyTree.clone_node_without_children(adv)
                    relation = AnyNode(name='ADV', spans=[{}], attributes=None, link='IS/ARE', nodeType='RELATION')
                    dep = Dependency(first, relation, second)
                    self.dependencies.append(dep)

    def detect_verb_noun_relationships(self):
        verbs = search.findall(self.root, filter_=lambda node: 'VERB' in node.attributes)
        for verb in verbs:
            nouns = search.findall(verb, filter_=lambda node: 'NOUN' in node.attributes or 'PROPN' in node.attributes)
            for noun in nouns:
                if (noun.parent == verb and noun.link == 'dep') or (noun.parent.parent == verb and noun.link == 'pobj'):
                    first = PlaceDependencyTree.clone_node_without_children(verb)
                    second = PlaceDependencyTree.clone_node_without_children(noun)
                    relation = AnyNode(name='OBJ', spans=[{}], attributes=None, link='HAS/RELATE', nodeType='RELATION')
                    dep = Dependency(first, relation, second)
                    self.dependencies.append(dep)

    def detect_units(self):
        numbers = search.findall(self.root, filter_= lambda node: 'NUM' in node.attributes)
        for num in numbers:
            context = num.parent
            if context is None:
                context = num
            units = search.findall(context, filter_= lambda node: node.name in node.link in ['dep', 'pobj'] and
                                                                  node.name in PlaceDependencyTree.UNITS)
            selected = None
            if len(units) == 1:
                selected = units[0]
            else:
                selected_depth = 1000
                for unit in units:
                    if selected_depth > unit.depth:
                        selected = unit
                        selected_depth = unit.depth

            if selected is not None:
                first = PlaceDependencyTree.clone_node_without_children(num)
                second = PlaceDependencyTree.clone_node_without_children(selected)
                relation = AnyNode(name='UNIT', spans=[{}], attributes=None, link='IS/ARE', nodeType='RELATION')
                dep = Dependency(first, relation, second)
                self.dependencies.append(dep)



    def detect_complex_prepositions(self):
        preps = search.findall(self.root, filter_=lambda node: node.link == 'prep')
        for prep in preps:
            if 'ADV' in prep.parent.attributes and len(prep.parent.children) == 1:
                first = PlaceDependencyTree.clone_node_without_children(prep)
                second = PlaceDependencyTree.clone_node_without_children(prep.parent)
                relation = AnyNode(name='PRP', spans=[{}], attributes=None, link='IS/ARE', nodeType='RELATION')
                dep = Dependency(first, relation, second)
                self.dependencies.append(dep)
            elif 'NUM' in prep.parent.attributes and len(prep.parent.children) > 1 \
                    and prep.parent.parent is not None and 'ADP' in prep.parent.parent.attributes:
                first = PlaceDependencyTree.clone_node_without_children(prep.parent.parent)
                relation = PlaceDependencyTree.clone_node_without_children(prep.parent)
                second = PlaceDependencyTree.clone_node_without_children(prep)
                dep = Dependency(first, relation, second)
                self.dependencies.append(dep)

                modifiers = search.findall(prep.parent, filter_=lambda node: 'ADV' in node.attributes and len(node.children) == 0)
                if len(modifiers) == 1:
                    relation = AnyNode(name='PRP', spans=[{}], attributes=None, link='IS/ARE', nodeType='RELATION')
                    second = PlaceDependencyTree.clone_node_without_children(modifiers[0])
                    dep = Dependency(first, relation, second)
                    self.dependencies.append(dep)


    @staticmethod
    def find_first_parent_based_on_attribute(node, attributes):
        ancestors = node.ancestors
        first_parent = None
        depth = 0
        for ancestor in ancestors:
            if ancestor.attributes[0] in attributes:
                if depth < ancestor.depth:
                    first_parent = ancestor
                    depth = ancestor.depth
        return first_parent

    @staticmethod
    def clone_node_without_children(node, override={}):
        if len(override) == 0:
            return AnyNode(name=node.name, spans=node.spans, attributes=node.attributes,
                       link=node.link, nodeType=node.nodeType)
        else:
            return AnyNode(name=node.name, spans=node.spans, attributes=override['attributes'],
                           link=override['link'], nodeType=override['nodeType'])

    def print_dependencies(self):
        for dep in self.dependencies:
            print(dep)