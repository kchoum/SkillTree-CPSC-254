# Beginner submission: Linked List implementation
# Intentional issues: == None instead of is None, no docstrings,
# manual counter increment, print-based testing, no edge case handling

class Node:
    def __init__(self, data):
        self.data = data
        self.next = None

class LinkedList:
    def __init__(self):
        self.head = None

    def append(self, data):
        new_node = Node(data)
        if self.head == None:
            self.head = new_node
            return
        current = self.head
        while current.next != None:
            current = current.next
        current.next = new_node

    def delete(self, data):
        if self.head == None:
            return
        if self.head.data == data:
            self.head = self.head.next
            return
        current = self.head
        while current.next != None:
            if current.next.data == data:
                current.next = current.next.next
                return
            current = current.next

    def print_list(self):
        elements = []
        current = self.head
        while current != None:
            elements.append(current.data)
            current = current.next
        print(elements)

    def length(self):
        count = 0
        current = self.head
        while current != None:
            count = count + 1
            current = current.next
        return count

my_list = LinkedList()
my_list.append(1)
my_list.append(2)
my_list.append(3)
my_list.delete(2)
my_list.print_list()
print(my_list.length())
