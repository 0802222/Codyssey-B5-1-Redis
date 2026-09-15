"""최소 힙 (Min-Heap).

배열(list) 기반의 완전 이진 트리로 구현한다. TTL 관리를 위해
(expire_at, key) 형태의 튜플을 원소로 다룰 수 있다 (튜플 비교는
첫 번째 값인 expire_at을 기준으로 이루어진다).
"""


class MinHeap:
    """부모가 항상 자식보다 작거나 같은 값을 갖는 최소 힙."""

    def __init__(self):
        self._data = []

    def size(self):
        return len(self._data)

    def is_empty(self):
        return len(self._data) == 0

    def peek(self):
        """최소 원소를 제거하지 않고 반환한다. 비어있으면 None."""
        if not self._data:
            return None
        return self._data[0]

    def push(self, item):
        """원소를 삽입하고 힙 성질을 복구한다. O(log n)."""
        self._data.append(item)
        self._heapify_up(len(self._data) - 1)

    def pop(self):
        """최소 원소를 제거하고 반환한다. 비어있으면 None. O(log n)."""
        if not self._data:
            return None
        top = self._data[0]
        last = self._data.pop()
        if self._data:
            self._data[0] = last
            self._heapify_down(0)
        return top

    def _heapify_up(self, idx):
        while idx > 0:
            parent = (idx - 1) // 2
            if self._data[idx] < self._data[parent]:
                self._data[idx], self._data[parent] = self._data[parent], self._data[idx]
                idx = parent
            else:
                break

    def _heapify_down(self, idx):
        n = len(self._data)
        while True:
            left = idx * 2 + 1
            right = idx * 2 + 2
            smallest = idx

            if left < n and self._data[left] < self._data[smallest]:
                smallest = left
            if right < n and self._data[right] < self._data[smallest]:
                smallest = right

            if smallest == idx:
                break

            self._data[idx], self._data[smallest] = self._data[smallest], self._data[idx]
            idx = smallest