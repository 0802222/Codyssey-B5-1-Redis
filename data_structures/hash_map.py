"""체이닝 방식 해시맵.

Python 내장 dict/set을 사용하지 않고, 버킷 테이블(list)과 직접 구현한
DoublyLinkedList로 충돌을 체이닝 방식으로 해결한다. 해시 함수도 직접
설계한다 (DJB2 변형).
"""

from data_structures.doubly_linked_list import DoublyLinkedList

_LOAD_FACTOR_LIMIT = 0.75
_INITIAL_CAPACITY = 8


class _Pair:
    """버킷 체인 안에서 key-value를 함께 보관하는 내부 컨테이너."""

    def __init__(self, key, value):
        self.key = key
        self.value = value


class HashMap:
    """문자열 key를 대상으로 하는 체이닝 방식 해시맵."""

    def __init__(self, initial_capacity=_INITIAL_CAPACITY):
        self._capacity = initial_capacity
        self._buckets: list[DoublyLinkedList | None] = [None] * self._capacity
        self._size = 0

    def _hash(self, key):
        """DJB2 기반 해시 함수. 문자열을 32비트 정수로 변환한다."""
        h = 5381
        for ch in key:
            h = ((h * 33) + ord(ch)) & 0xFFFFFFFF
        return h

    def _index_for(self, key, capacity):
        return self._hash(key) % capacity

    def _find_node(self, key):
        idx = self._index_for(key, self._capacity)
        bucket = self._buckets[idx]
        if bucket is None:
            return None, idx
        node = bucket.head
        while node is not None:
            if node.data.key == key:
                return node, idx
            node = node.next
        return None, idx
    
    def put(self, key, value):
        """key가 있으면 값을 갱신하고, 없으면 새로 삽입한다."""
        node, idx = self._find_node(key)
        if node is not None:
            node.data.value = value
            return

        bucket = self._buckets[idx]
        if bucket is None:
            bucket = DoublyLinkedList()
            self._buckets[idx] = bucket
        bucket.insert_back(_Pair(key, value))
        self._size += 1

        if self._size / self._capacity > _LOAD_FACTOR_LIMIT:
            self._resize(self._capacity * 2)

    def get(self, key):
        """key에 해당하는 값을 반환한다. 없으면 None."""
        node, _ = self._find_node(key)
        return node.data.value if node is not None else None

    def remove(self, key):
        """key를 제거하고 제거된 값을 반환한다. 없으면 None."""
        idx = self._index_for(key, self._capacity)
        bucket = self._buckets[idx]
        if bucket is None:
            return None
        node = bucket.head
        while node is not None:
            if node.data.key == key:
                value = node.data.value
                bucket.remove_node(node)
                self._size -= 1
                return value
            node = node.next
        return None

    def contains(self, key):
        node, _ = self._find_node(key)
        return node is not None

    def keys(self):
        """저장된 모든 key를 리스트로 반환한다 (순서 보장 없음)."""
        result = []
        for bucket in self._buckets:
            if bucket is None:
                continue
            node = bucket.head
            while node is not None:
                result.append(node.data.key)
                node = node.next
        return result

    def size(self):
        return self._size

    def _resize(self, new_capacity):
        """로드 팩터 초과 시 버킷 테이블을 확장하고 모든 항목을 재해싱한다."""
        old_buckets = self._buckets
        self._capacity = new_capacity
        self._buckets = [None] * new_capacity

        for bucket in old_buckets:
            if bucket is None:
                continue
            node = bucket.head
            while node is not None:
                idx = self._index_for(node.data.key, self._capacity)
                target_bucket = self._buckets[idx]
                if target_bucket is None:
                    target_bucket = DoublyLinkedList()
                    self._buckets[idx] = target_bucket
                target_bucket.insert_back(_Pair(node.data.key, node.data.value))
                node = node.next