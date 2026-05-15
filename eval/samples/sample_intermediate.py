# Intermediate submission: Binary Search Tree
# Issues: no balance checking, delete only handles leaf nodes,
# search returns None implicitly instead of False, inconsistent return types

class BSTNode:
    def __init__(self, val):
        self.val = val
        self.left = None
        self.right = None

class BST:
    def __init__(self):
        self.root = None

    def insert(self, val):
        if self.root is None:
            self.root = BSTNode(val)
        else:
            self._insert(self.root, val)

    def _insert(self, node, val):
        if val < node.val:
            if node.left is None:
                node.left = BSTNode(val)
            else:
                self._insert(node.left, val)
        else:
            if node.right is None:
                node.right = BSTNode(val)
            else:
                self._insert(node.right, val)

    def search(self, val):
        return self._search(self.root, val)

    def _search(self, node, val):
        if node is None:
            return  # should return False
        if node.val == val:
            return True
        elif val < node.val:
            return self._search(node.left, val)
        else:
            return self._search(node.right, val)

    def inorder(self):
        result = []
        self._inorder(self.root, result)
        return result

    def _inorder(self, node, result):
        if node:
            self._inorder(node.left, result)
            result.append(node.val)
            self._inorder(node.right, result)

    def delete(self, val):
        # Only handles leaf node deletion
        if self.root is None:
            return
        parent = None
        current = self.root
        while current and current.val != val:
            parent = current
            if val < current.val:
                current = current.left
            else:
                current = current.right
        if current is None:
            return
        if current.left is None and current.right is None:
            if parent is None:
                self.root = None
            elif parent.left == current:
                parent.left = None
            else:
                parent.right = None

tree = BST()
for v in [5, 3, 7, 1, 4, 6, 8]:
    tree.insert(v)

print(tree.inorder())
print(tree.search(4))
print(tree.search(9))
tree.delete(1)
print(tree.inorder())
