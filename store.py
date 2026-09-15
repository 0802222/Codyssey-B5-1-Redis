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


class MiniRedisStore:
    """String 타입 + LRU + TTL을 지원하는 In-Memory Key-Value 저장소."""

    def __init__(self):
        self._map = HashMap()           # key -> _Entry
        self._lru = DoublyLinkedList()  # head=가장 최근 사용, tail=가장 오래됨 (data=key)
        self._ttl_heap = MinHeap()      # (expire_at, key) 최소 힙 (lazy deletion)

        self.maxmemory = 0
        self.used_memory = 0
        self.evicted_keys = 0

    # ------------------------------------------------------------------
    # 만료 처리 (TTL)
    # ------------------------------------------------------------------
    def _delete_key(self, key):
        """key 관련 데이터/LRU/TTL 구조를 모두 제거한다."""
        entry = self._map.remove(key)
        if entry is None:
            return None
        self._lru.remove_node(entry.lru_node)
        self.used_memory -= _entry_size(key, entry.value)
        return entry

    def _purge_if_expired(self, key):
        """key가 만료되었다면 즉시 삭제한다 (lazy deletion). 만료되었으면 True."""
        entry = self._map.get(key)
        if entry is not None and entry.expire_at is not None and entry.expire_at <= time.time():
            self._delete_key(key)
            return True
        return False

    def sweep_expired(self):
        """힙의 최소값(가장 빨리 만료되는 key)부터 확인해 능동적으로 만료를 정리한다.

        힙에는 과거에 설정된 TTL의 잔재(stale entry)가 남아 있을 수 있으므로,
        pop한 항목이 현재 entry의 expire_at과 일치할 때만 실제로 삭제한다.
        """
        now = time.time()
        while True:
            top = self._ttl_heap.peek()
            if top is None or top[0] > now:
                break
            expire_at, key = self._ttl_heap.pop()
            entry = self._map.get(key)
            if entry is not None and entry.expire_at == expire_at:
                self._delete_key(key)
                
    # ------------------------------------------------------------------
    # 메모리 관리 + LRU 제거
    # ------------------------------------------------------------------
    def _evict_one_lru(self):
        key = self._lru.remove_back()
        if key is None:
            return False
        entry = self._map.remove(key)
        if entry is None:
            return False
        self.used_memory -= _entry_size(key, entry.value)
        self.evicted_keys += 1
        return True

    def config_set_maxmemory(self, bytes_value):
        if bytes_value < 0:
            raise MiniRedisError(ERR_NOT_INTEGER)
        self.maxmemory = bytes_value
        return "OK"

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