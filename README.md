# 정보를 엄청 빠르게 찾아주는 작은 저장소 만들기

<br>

## 과제 개요
이 과제는 `Redis` 를 이용해 정보를 빠르게 찾아주는 작은 저장소를 만드는 미션이다.

평소 레디스가 빠르다는건 알고있지만, 그 속에 있는 `HashMap`(빠른 Key-value 저장), `연결리스트` (LRU), `Heap`(TTL) 을 직접 만들어보면서 왜 빠른지 체감할 수 있는 미션이다.

### Redis란?
`Remote Dictionary Server`로, 데이터를 DISK가 아니라 `MEMORY`(RAM)에 저장하는 저장소 이다.

캐시(자주 조회하는 데이터를 잠깐 저장해서 DB 부담 줄이기), 세션 저장, 실시간 랭킹 등에 사용된다.

- 일반 DB와 Redis 의 비교

    | 구분 | 저장 위치 | 설명
    | -- | -- | -- | 
    | 일반 DB | 디스크 | 안정적이지만 느림 |
    | Redis (In-Memory DB) | 메모리 | 전원 꺼지면 휘발되지만 대신 훨씬 빠름 |


<br>

## 자료구조
Redis 가 빠른 이유는 각 문제(조회, 제거 우선순위, 만료 우선순위)에 딱 맞는 자료구조를 골라 조합했기 때문이다.
이번 미션은 그 조합을 dict 나 set 같은 내장도구 없이 직접 짜보면서, 왜 O(1) 이 되는지 체감할 수 있다.

|  자료구조 | 정의 |  상황	| 필요한 연산 | 
| -- | -- | -- | -- |
| HashMap | Key를 숫자로 변환(Hash)해서 배열 칸에 저장하는 구조 | 값을 저장/조회	| key로 `O(1)` 접근	| 해시맵 |
| 이중 연결 리스트 | 노드들이 `Prev`(이전 노드 주소), `Next`(다음 노드 주소)를 서로 들고 있는 구조 | 메모리 초과 시 뭘 지울지 | "가장 오래 안 쓴 것" `O(1)` 파악 | 	
| 최소 힙 | `부모가` 항상 자식보다 `작은 값을 가지는` 배열 기반 트리 | TTL 만료 시 뭘 지울지 | "가장 빨리 만료될 것" `O(log n)` 파악 |



<br>

## 프로젝트 구조
```
main.py                              # 실행 진입점 (python main.py)
mini_redis/
├── data_structures/
│   ├── doubly_linked_list.py        # 이중 연결 리스트 (Node, DoublyLinkedList)
│   ├── hash_map.py                  # 체이닝 방식 해시맵 (직접 설계한 해시 함수)
│   └── min_heap.py                  # 최소 힙 (TTL 관리)
├── store.py                         # 핵심 엔진: SET/GET/DEL + LRU + TTL + 메모리 관리
├── commands.py                      # 명령어 파싱/디스패치 + Redis 스타일 출력 포맷
└── cli.py                           # REPL 루프
tests/                                # 자료구조 및 명령어 단위 테스트
```

## 실행 방법
```bash
python3 main.py
```

## 테스트 실행
```bash
python3 -m unittest discover -s tests
```

## 지원 명령어
- String: `SET`, `GET`, `DEL`, `EXISTS`, `DBSIZE`, `KEYS`
- 메모리 관리: `CONFIG SET maxmemory <bytes>`, `INFO memory`
- TTL: `EXPIRE <key> <seconds>`, `TTL <key>`
- 종료: `exit` / `quit`

## 동작 규칙
- `CONFIG SET maxmemory 0` : 0은 "무제한"을 의미하며, 이 경우 LRU 자동 제거가 동작하지 않는다.
- `EXPIRE key seconds` : seconds가 0 이하이면 "즉시 만료"로 처리되어 해당 key가 즉시 삭제된다.

### 실행 예시
```python
mini-redis> CONFIG SET maxmemory 30
OK
mini-redis> SET user:1 "Alice"
OK
mini-redis> SET user:2 "Bob"
OK
mini-redis> SET user:3 "Charlie"
OK
mini-redis> GET user:1
(nil)                          # maxmemory 초과로 LRU였던 user:1이 자동 제거됨
mini-redis> INFO memory
used_memory:22
maxmemory:30
evicted_keys:1
```
## 제약 사항 준수
- `dict`, `set`, `collections` 미사용 (해시맵/캐시/명령어 디스패치 테이블 모두 직접 구현한 자료구조 또는 list 기반으로 처리)
- 네트워크 통신, 파일 영속성, List/Set/Sorted Set, 멀티스레딩은 구현하지 않음 (요구사항 범위 외)