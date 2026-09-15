"""명령어 파싱 + 실행 + Redis 스타일 출력 포맷."""

from store import MiniRedisError, parse_int


def tokenize(line):
    """공백으로 토큰을 나누되, 큰따옴표로 감싼 구간은 하나의 토큰으로 취급한다.

    예) SET user:1 "Alice Kim"  ->  ["SET", "user:1", "Alice Kim"]
    """
    tokens = []
    i, n = 0, len(line)

    while i < n:
        while i < n and line[i] == " ":
            i += 1
        if i >= n:
            break

        if line[i] == '"':
            j = i + 1
            buf = []
            while j < n and line[j] != '"':
                buf.append(line[j])
                j += 1
            tokens.append("".join(buf))
            i = j + 1
        else:
            j = i
            while j < n and line[j] != " ":
                j += 1
            tokens.append(line[i:j])
            i = j

    return tokens


def fmt_ok():
    return "OK"


def fmt_nil():
    return "(nil)"


def fmt_integer(n):
    return f"(integer) {n}"


def fmt_bulk_string(s):
    return f'"{s}"'


def fmt_error(message):
    return f"(error) {message}"


def fmt_keys(keys_list):
    if not keys_list:
        return "(empty array)"
    lines = [f'{i}. "{key}"' for i, key in enumerate(keys_list, start=1)]
    return "\n".join(lines)


def _require_argc(cmd_name, args, expected):
    if len(args) != expected:
        raise MiniRedisError(f"ERR wrong number of arguments for '{cmd_name}' command")


class CommandDispatcher:
    """토큰화된 명령어를 store에 위임하고 결과를 Redis 스타일 문자열로 포맷한다."""

    def __init__(self, store):
        self.store = store

    def execute(self, line):
        tokens = tokenize(line)
        if not tokens:
            return None  # 빈 입력은 아무 것도 출력하지 않는다

        raw_cmd = tokens[0]
        cmd = raw_cmd.upper()
        args = tokens[1:]

        if cmd in ("EXIT", "QUIT"):
            return "__EXIT__"

        # 명령어 실행 전, 힙을 이용해 이미 만료된 key들을 능동적으로 정리한다.
        self.store.sweep_expired()

        handler = self._find_handler(cmd)
        if handler is None:
            return fmt_error(f"ERR unknown command '{raw_cmd}'")

        try:
            return handler(self, raw_cmd, args)
        except MiniRedisError as exc:
            return fmt_error(str(exc))

    # ------------------------------------------------------------------
    # String 명령어
    # ------------------------------------------------------------------
    def _cmd_set(self, raw_cmd, args):
        _require_argc(raw_cmd, args, 2)
        key, value = args
        self.store.set(key, value)
        return fmt_ok()

    def _cmd_get(self, raw_cmd, args):
        _require_argc(raw_cmd, args, 1)
        value = self.store.get(args[0])
        return fmt_nil() if value is None else fmt_bulk_string(value)

    def _cmd_del(self, raw_cmd, args):
        _require_argc(raw_cmd, args, 1)
        return fmt_integer(self.store.delete(args[0]))

    def _cmd_exists(self, raw_cmd, args):
        _require_argc(raw_cmd, args, 1)
        return fmt_integer(self.store.exists(args[0]))

    def _cmd_dbsize(self, raw_cmd, args):
        _require_argc(raw_cmd, args, 0)
        return fmt_integer(self.store.dbsize())

    def _cmd_keys(self, raw_cmd, args):
        _require_argc(raw_cmd, args, 0)
        return fmt_keys(self.store.keys())

    # ------------------------------------------------------------------
    # 메모리 관리 명령어
    # ------------------------------------------------------------------
    def _cmd_config(self, raw_cmd, args):
        if len(args) != 3 or args[0].upper() != "SET" or args[1].lower() != "maxmemory":
            raise MiniRedisError(f"ERR wrong number of arguments for '{raw_cmd}' command")
        bytes_value = parse_int(args[2])
        self.store.config_set_maxmemory(bytes_value)
        return fmt_ok()

    def _cmd_info(self, raw_cmd, args):
        _require_argc(raw_cmd, args, 1)
        if args[0].lower() != "memory":
            raise MiniRedisError(f"ERR unknown INFO section '{args[0]}'")
        return self.store.info_memory()

    # ------------------------------------------------------------------
    # TTL 명령어
    # ------------------------------------------------------------------
    def _cmd_expire(self, raw_cmd, args):
        _require_argc(raw_cmd, args, 2)
        key, seconds_token = args
        seconds = parse_int(seconds_token)
        return fmt_integer(self.store.expire(key, seconds))

    def _cmd_ttl(self, raw_cmd, args):
        _require_argc(raw_cmd, args, 1)
        return fmt_integer(self.store.ttl(args[0]))

    # dict 없이 (명령어 이름, 핸들러) 쌍의 리스트로 디스패치 테이블을 구성한다.
    _HANDLER_TABLE = [
        ("SET", _cmd_set),
        ("GET", _cmd_get),
        ("DEL", _cmd_del),
        ("EXISTS", _cmd_exists),
        ("DBSIZE", _cmd_dbsize),
        ("KEYS", _cmd_keys),
        ("CONFIG", _cmd_config),
        ("INFO", _cmd_info),
        ("EXPIRE", _cmd_expire),
        ("TTL", _cmd_ttl),
    ]

    def _find_handler(self, cmd):
        for name, handler in self._HANDLER_TABLE:
            if name == cmd:
                return handler
        return None