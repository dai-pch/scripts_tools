
import collections.deque as deque
class Tree(object):
    class TreeNode(object):
        def __init__(self, data=None, name=None, parent=None):
            self.__children = set()
            self.name = name
            self.data = data
            if parent is None:
                self.__parent = None
            else:
                self.given_to(parent)

        def given_to(self, parent):
            if not self.__parent is None:
                self.__parent.__children.remove(self)
            self.__parent = parent
            parent.children.add(self)

        def get_depth(self):
            if self.__parent is None:
                return 0
            else:
                return self.__parent.get_depth() + 1

        def get_children(self):
            return self.__children

        def get_parent(self):
            return self.__parent

        def add_child(self, data, name):
            child = TreeNode(data, name, self)
        
    def __init__(self):
        self.head = TreeNode()

    def depth_first_traverse(self, func, root=None):
        if root is None:
            root = self.head
        for node in self.children:
            self.depth_first_traverse(func, node)
        func(root)

    def width_first_traverse(self, func, root=None):
        if root is None:
            root = self.head
        que = deque()
        que.append(root)
        while not que.empty():
            cur = que.popleft()
            que.extend(cur.get_children())
            func(cur)
    
