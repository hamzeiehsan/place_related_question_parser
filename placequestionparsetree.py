from anytree import AnyNode, RenderTree
import anytree.cachedsearch as search


# class NodeClass(NodeMixin):
#     def __init__(self, name, nodeType, role='', parent=None, children=None):
#         super(NodeClass, self).__init__()
#         self.name = name
#         self.role = role
#         self.nodeType = nodeType
#         if children:
#             self.children = children
#
#     def get_name(self):
#         return self.name
#
#     def get_role(self):
#         return self.role
#
#     def set_role(self, role):
#         self.role = role
#
#     def __repr__(self):
#         return self.name+"{"+self.role+"} "


class PlaceQuestionParseTree:
    def __init__(self, parse_dict):
        self.parse_dict = parse_dict
        self.tree = None
        self.construct_tree()

    def construct_tree(self):
        root = AnyNode(name=self.parse_dict['word'], nodeType=self.parse_dict['nodeType'], role='')
        temp = self.parse_dict

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
        return False