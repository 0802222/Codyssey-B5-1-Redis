"""REPL(Read-Eval-Print Loop) 인터페이스."""

from commands import CommandDispatcher
from store import MiniRedisStore

PROMPT = "mini-redis> "


def run():
    store = MiniRedisStore()
    dispatcher = CommandDispatcher(store)

    while True:
        try:
            line = input(PROMPT)
        except (EOFError, KeyboardInterrupt):
            print()
            break

        result = dispatcher.execute(line)
        if result is None:
            continue
        if result == "__EXIT__":
            break
        print(result)


if __name__ == "__main__":
    run()