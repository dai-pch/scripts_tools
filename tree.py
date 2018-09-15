
from collections import deque
class TreeNode(object):
    def __init__(self, data=None, name=None, parent=None):
        self.__children = set()
        self.__parent = None
        self.name = name
        self.data = data
        if not parent is None:
            self.given_to(parent)

    def given_to(self, parent):
        if not self.__parent is None:
            self.__parent.__children.remove(self)
        self.__parent = parent
        parent.__children.add(self)

    def get_depth(self):
        if self.__parent is None:
            return 1
        else:
            return self.__parent.get_depth() + 1

    def get_children(self):
        return self.__children

    def get_parent(self):
        return self.__parent

    def add_child(self, data, name):
        child = TreeNode(data, name, self)
        return child
        
    def get_level(self):
        leaf_depth = 0
        def helper(n):
            nonlocal leaf_depth
            leaf_depth = max(n.get_depth(), leaf_depth)
        self.depth_first_traverse(func_leaf=helper)
        return leaf_depth - self.get_depth() + 1

    def depth_first_traverse(self, func=None, func_leaf=None, max_depth=-1):
        if max_depth == 0 or not self.__children:
            if not func_leaf is None:
                func_leaf(self)
        else:
            for child in self.__children:
                child.depth_first_traverse(func, func_leaf, max_depth-1)
        if not func is None:
            func(self)

    def width_first_traverse(self, func):
        que = deque()
        que.append(self)
        while not que.empty():
            cur = que.popleft()
            que.extend(cur.__children)
            func(cur)
    
    def get_next_n_nodes(self, depth):
        if depth == 0:
            return [([], self)]
        else:
            node_list = []
            for child in self.__children:
                node_list += child.get_next_n_nodes(depth - 1)
            return map(lambda arg: ([arg[1].name] + arg[0], arg[1]), node_list)

    def extend_dict(self, dic):
        if not isinstance(dic, dict):
            self.data = dic
        elif dic:
            for key, value in dic.items():
                child = self.add_child(None, key)
                child.extend_dict(value)

    def get_child_by_name(self, name):
        for child in self.__children:
            if child.name == name:
                return child
        return None

    def get_child_by_path(self, path):
        if not path:
            return self
        node = self.get_child_by_name(path.pop(0))
        if node:
            return node.get_child_by_path(path)
        else:
            return None

    def __str__(self):
        return "{name: " + str(self.name) + ", data: " + str(self.data) + ", children: " + ", ".join([str(child) for child in self.__children]) + "}"

    def display(self, level=0):
        pre = ''
        if level > 1:
            pre = "| "*(level-1)
        print(pre, end='')
        if level > 0:
            print('|-', end='')
        print("o" + '"' + str(self.name) +'": ' + str(self.data))
        for node in self.__children:
            node.display(level+1)


class Tree(object):
    def __init__(self):
        self.root = TreeNode()
    
    def display(self):
        self.root.display()

    def tree_depth(self):
        return self.root.get_level()

    @staticmethod
    def extract_path(ancestor, node):
        path = []
        while node:
            if not node is ancestor:
                path = [node.name] + path
                node = node.get_parent()
            else:
                break
        return path

    @staticmethod
    def from_dict(dic_root, root_name=None):
        tree = Tree()
        tree.root.name = root_name
        tree.root.extend_dict(dic_root)
        return tree

