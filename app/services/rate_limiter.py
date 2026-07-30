import time

from app.repositories.file_store import FileStore


class RateLimitExceeded(Exception):
    def __init__(self, retry_after: int):
        self.retry_after = retry_after
        super().__init__("rate limit exceeded")


class FileRateLimiter:
    def __init__(self, store: FileStore, max_requests: int, window_seconds: int):
        self.store = store
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    def check(self, client_key: str) -> None:
        now = time.time()
        records = self.store.load_rate_limits()
        recent = [timestamp for timestamp in records.get(client_key, []) if now - timestamp < self.window_seconds]
        if len(recent) >= self.max_requests:
            retry_after = max(1, int(self.window_seconds - (now - min(recent))) + 1)
            records[client_key] = recent
            self.store.save_rate_limits(records)
            raise RateLimitExceeded(retry_after)
        recent.append(now)
        records[client_key] = recent
        self.store.save_rate_limits(records)

