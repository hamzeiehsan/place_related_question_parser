from anytree import AnyNode, RenderTree, PostOrderIter
import anytree.cachedsearch as search


class PlaceQuestionParseTree:
    def __init__(self, parse_dict):
        self.parse_dict = parse_dict
        self.tree = None
        self.root = None
        self.construct_tree()

    def construct_tree(self):
        root = AnyNode(name=self.parse_dict['word'], nodeType=self.parse_dict['nodeType'], role='')
        if 'children' in self.parse_dict.keys():
            for child in self.parse_dict['children']:
                self.add_to_tree(child, root)
        self.root = root
        self.tree = RenderTree(root)

    def add_to_tree(self, node, parent):
        n = AnyNode(name=node['word'], nodeType=node['nodeType'], parent=parent, role='')
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
            res+="%s%s (%s) {%s}" % (pre, node.name, node.nodeType, node.role)+"\n"
        return res

    def find_node_by_exact_name(self, string):
         return search.findall_by_attr(self.root, string)

    def find_node_by_name(self, string):
        res = self.find_node_by_exact_name(string)
        if len(res) > 0:
            return res
        return search.findall(self.root, filter_=lambda node: node.name in string.split())

    def label_role(self, name, role, clean=False):
        nodes = self.find_node_by_name(name)
        if len(nodes) == 1:
            nodes[0].role = role
            if clean:
                nodes[0].children = []
            return True
        else:
            for node in nodes:
                if node.nodeType.startswith("N"):
                    node.role = role
                    if clean:
                        node.children = []
        return False

    def clean_tree(self):
        named_objects = search.findall(self.root, filter_=lambda node: node.role in ("E", "P", "e", "p", "d", "o"))
        for named_object in named_objects:
            if len(named_object.siblings) == 1 and named_object.siblings[0].nodeType == 'DT':
                named_object.parent.role = named_object.role
                named_object.parent.children = []

    def label_spatiotemporal_relationships(self):
        named_objects = search.findall(self.root, filter_=lambda node: node.role in ("P", "p", "d"))
        for named_object in named_objects:
            for sibling in named_object.siblings:
                if sibling.nodeType == 'IN' and named_object.parent.nodeType.startswith('PP'):
                    sibling.role = 'r'
                    if len(named_object.siblings) == 1:
                        named_object.parent.role = 'LOCATION'
                    else:
                        node = AnyNode(name=sibling.name+' '+named_object.name, nodeType='PP', role='LOCATION')
                        node.parent = named_object.parent
                        named_object.parent = node
                        sibling.parent = node
                    break

    def clean_locations(self):
        # todo conjunction not yet implemented but should take place before calling this function
        named_objects = search.findall(self.root, filter_=lambda node: node.role == 'LOCATION')
        if len(named_objects) == 2: # todo more complex combinations are ignore: select if they belong to same VP parent
            if named_objects[0].depth < named_objects[1].depth:
                if self.root.name.index(named_objects[0].name) < self.root.name.index(named_objects[1].name):
                    self.merge(node1=named_objects[0], node2=named_objects[1])
                else:
                    self.merge(node1=named_objects[0], node2=named_objects[1], order=False)
            else:
                if self.root.name.index(named_objects[0].name) < self.root.name.index(named_objects[1].name):
                    self.merge(node1=named_objects[1], node2=named_objects[0], order=False)
                else:
                    self.merge(node1=named_objects[1], node2=named_objects[0])

    def merge(self, node1, node2, order=True):
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
        for npo in npos:
            npo.role = 'o'

        for npo in npos:
            parent = npo.parent
            if parent is not None:
                all_objects = True
                for child in parent.children:
                    if child.role != 'o' and child.nodeType != 'DT':
                        all_objects = False
                if all_objects:
                    parent.role = 'o'
                    parent.children = []