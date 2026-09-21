"""이중 연결 리스트 (Doubly Linked List).

해시맵의 체이닝(충돌 해결)과 LRU 순서 추적에 재사용된다.
모든 삽입/삭제/이동 연산은 노드 참조만 있으면 O(1)에 동작한다.
"""


class Node:
    """이중 연결 리스트의 노드. prev/next/data 필드를 가진다."""

    def __init__(self, data):
        self.data = data
        self.prev: Node | None = None
        self.next: Node | None = None


class DoublyLinkedList:
    """head/tail을 직접 관리하는 이중 연결 리스트."""

    def __init__(self):
        self.head = None
        self.tail = None
        self._size = 0

    def size(self):
        return self._size

    def is_empty(self):
        return self._size == 0

    def insert_front(self, data):
        """맨 앞에 새 노드를 삽입하고 그 노드를 반환한다. O(1)."""
        node = Node(data)
        if self.head is None:
            self.head = node
            self.tail = node
        else:
            node.next = self.head
            self.head.prev = node
            self.head = node
        
        self._size += 1
        return node

    def insert_back(self, data):
        """맨 뒤에 새 노드를 삽입하고 그 노드를 반환한다. O(1)."""
        node = Node(data)
        if self.tail is None:
            self.head = node
            self.tail = node
        else:
            node.prev = self.tail
            self.tail.next = node
            self.tail = node
        self._size += 1
        return node

    def remove_front(self):
        """맨 앞 노드를 제거하고 그 data를 반환한다 (없으면 None). O(1)."""
        if self.head is None:
            return None
        return self.remove_node(self.head)

    def remove_back(self):
        """맨 뒤 노드를 제거하고 그 data를 반환한다 (없으면 None). O(1)."""
        if self.tail is None:
            return None
        return self.remove_node(self.tail)

    def remove_node(self, node):
        """임의의 노드를 리스트에서 제거하고 그 data를 반환한다. O(1)."""
        if node is None:
            return None

        if node.prev is not None:
            node.prev.next = node.next
        else:
            self.head = node.next

        if node.next is not None:
            node.next.prev = node.prev
        else:
            self.tail = node.prev

        node.prev = None
        node.next = None
        self._size -= 1
        return node.data

    def move_to_front(self, node):
        """이미 리스트에 있는 노드를 맨 앞으로 옮긴다. O(1)."""
        if node is None or node is self.head:
            return
        # 연결을 끊지 않고 포인터만 재배치한다 (remove + insert로 인한
        # 임시 노드 생성을 피해 O(1)을 유지한다).
        if node.prev is not None:
            node.prev.next = node.next
        if node.next is not None:
            node.next.prev = node.prev
        if node is self.tail:
            self.tail = node.prev

        node.prev = None
        node.next = self.head
        if self.head is not None:
            self.head.prev = node
        self.head = node
        if self.tail is None:
            self.tail = node