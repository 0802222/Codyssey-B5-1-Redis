"""Mini Redis 핵심 엔진.

직접 구현한 HashMap / DoublyLinkedList / MinHeap을 조합하여
SET/GET/DEL 등의 String 명령어, LRU 기반 메모리 제거, 힙 기반
TTL 관리를 수행한다.
"""

import time

from data_structures.doubly_linked_list import DoublyLinkedList
from data_structures.hash_map import HashMap
from data_structures.min_heap import MinHeap


class MiniRedisError(Exception):
    """CLI 표준 에러 메시지를 그대로 담아 전달하는 예외."""


ERR_NOT_INTEGER = "ERR value is not an integer or out of range"
ERR_OOM = "OOM command not allowed when used_memory > 'maxmemory'"


def parse_int(token):
    """느슨한 int() 대신, 부호+숫자로만 이루어진 정수만 허용한다."""
    if not token:
        raise MiniRedisError(ERR_NOT_INTEGER)

    idx = 0
    sign = 1
    if token[0] in "+-":
        idx = 1
        if token[0] == "-":
            sign = -1

    digits = token[idx:]
    if not digits or not digits.isdigit():
        raise MiniRedisError(ERR_NOT_INTEGER)

    return sign * int(digits)


class _Entry:
    """해시맵에 저장되는 실제 값 컨테이너. LRU 노드와 만료 시각을 함께 가진다."""

    def __init__(self, value, lru_node):
        self.value = value
        self.lru_node = lru_node
        self.expire_at = None  # None이면 TTL 없음


    def _entry_size(key, value):
        """used_memory 산정 공식: len(utf8(key)) + len(utf8(value))."""
        return len(key.encode("utf-8")) + len(value.encode("utf-8"))

    def info_memory(self):
        return (
            f"used_memory:{self.used_memory}\n"
            f"maxmemory:{self.maxmemory}\n"
            f"evicted_keys:{self.evicted_keys}"
        )

    # ------------------------------------------------------------------
    # String 명령어
    # ------------------------------------------------------------------
    def set(self, key, value):
        self._purge_if_expired(key)

        new_size = _entry_size(key, value)
        if self.maxmemory > 0 and new_size > self.maxmemory:
            raise MiniRedisError(ERR_OOM)

        existing = self._map.get(key)
        if existing is not None:
            self.used_memory -= _entry_size(key, existing.value)
            existing.value = value
            existing.expire_at = None  # 기존 키를 덮어쓰면 TTL은 초기화(삭제)
            self._lru.move_to_front(existing.lru_node)
        else:
            node = self._lru.insert_front(key)
            self._map.put(key, _Entry(value, node))

        self.used_memory += new_size

        while self.maxmemory > 0 and self.used_memory > self.maxmemory:
            if not self._evict_one_lru():
                break

        return "OK"

    def get(self, key):
        self._purge_if_expired(key)
        entry = self._map.get(key)
        if entry is None:
            return None
        self._lru.move_to_front(entry.lru_node)
        return entry.value

    def delete(self, key):
        self._purge_if_expired(key)
        return 1 if self._delete_key(key) is not None else 0

    def exists(self, key):
        self._purge_if_expired(key)
        return 1 if self._map.contains(key) else 0

    def dbsize(self):
        return self._map.size()

    def keys(self):
        return self._map.keys()

    # ------------------------------------------------------------------
    # TTL 명령어
    # ------------------------------------------------------------------
    def expire(self, key, seconds):
        self._purge_if_expired(key)
        entry = self._map.get(key)
        if entry is None:
            return 0

        if seconds <= 0:
            self._delete_key(key)
            return 1

        entry.expire_at = time.time() + seconds
        self._ttl_heap.push((entry.expire_at, key))
        return 1

    def ttl(self, key):
        self._purge_if_expired(key)
        entry = self._map.get(key)
        if entry is None:
            return -2
        if entry.expire_at is None:
            return -1

        remaining = entry.expire_at - time.time()
        if remaining <= 0:
            self._delete_key(key)
            return -2
        return int(remaining)