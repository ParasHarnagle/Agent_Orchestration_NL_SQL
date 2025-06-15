# trace_to_queue.py
import logging, asyncio, json, re

LOG_LINE_RE = re.compile(r"^(={5}|<{5}).*Supervisor .*?:\s*", re.S)

class TraceQueueHandler(logging.Handler):
    """
    Thread-safe: pushes supervisor trace lines onto an asyncio.Queue
    using loop.call_soon_threadsafe, so it never needs its own
    create_task().
    """
    def __init__(self, queue: asyncio.Queue, loop: asyncio.AbstractEventLoop):
        super().__init__(level=logging.INFO)
        self.q    = queue
        self.loop = loop           # ← store the main loop

    def emit(self, record: logging.LogRecord):
        msg = record.getMessage()
        if LOG_LINE_RE.match(msg):
            direction = "tool_call" if msg.startswith("===>>>>>") else "tool_result"
            payload   = msg.split(":", 1)[1].strip()[:800]

            # thread-safe handoff to the main loop
            self.loop.call_soon_threadsafe(
                self.q.put_nowait,
                {
                    "event": direction,
                    "data" : {"log": payload}
                }
            )
