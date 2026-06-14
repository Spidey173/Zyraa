import redis
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

# Initialize connection pool for performance optimization
import sys
IS_TESTING = 'test' in sys.argv

class MockRedisPipeline:
    def __init__(self, client):
        self.client = client
        self.commands = []

    def zadd(self, key, mapping, *args, **kwargs):
        self.commands.append(('zadd', key, mapping))
        return self

    def zremrangebyrank(self, key, start, end):
        self.commands.append(('zremrangebyrank', key, start, end))
        return self

    def execute(self):
        results = []
        for cmd in self.commands:
            op = cmd[0]
            if op == 'zadd':
                results.append(self.client.zadd(cmd[1], cmd[2]))
            elif op == 'zremrangebyrank':
                results.append(self.client.zremrangebyrank(cmd[1], cmd[2], cmd[3]))
        self.commands = []
        return results

class MockRedis:
    def __init__(self):
        self.data = {}  # key -> structure (dict or set or dict score)
        self.expirations = {}

    def ping(self):
        return True

    def flushdb(self):
        self.data.clear()
        self.expirations.clear()

    def delete(self, *keys):
        for k in keys:
            self.data.pop(k, None)

    def sadd(self, key, member):
        if key not in self.data:
            self.data[key] = set()
        self.data[key].add(member)
        return 1

    def srem(self, key, member):
        if key in self.data and member in self.data[key]:
            self.data[key].remove(member)
            return 1
        return 0

    def zadd(self, key, mapping, *args, **kwargs):
        if key not in self.data:
            self.data[key] = {}  # member -> score
        for member, score in mapping.items():
            self.data[key][member] = float(score)
        return len(mapping)

    def zincrby(self, key, amount, member):
        if key not in self.data:
            self.data[key] = {}
        old_score = self.data[key].get(member, 0.0)
        new_score = old_score + float(amount)
        self.data[key][member] = new_score
        return new_score

    def zrevrange(self, key, start, end):
        if key not in self.data:
            return []
        sorted_members = sorted(self.data[key].items(), key=lambda x: x[1], reverse=True)
        members = [m[0] for m in sorted_members]
        if end == -1:
            return [str(m).encode('utf-8') for m in members[start:]]
        return [str(m).encode('utf-8') for m in members[start:end+1]]

    def zremrangebyrank(self, key, start, end):
        if key not in self.data:
            return 0
        sorted_members = sorted(self.data[key].items(), key=lambda x: x[1])
        n = len(sorted_members)
        s = start if start >= 0 else n + start
        e = end if end >= 0 else n + end
        to_remove = sorted_members[s:e+1]
        removed = 0
        for m, _ in to_remove:
            self.data[key].pop(m, None)
            removed += 1
        return removed

    def zremrangebyscore(self, key, min_val, max_val):
        if key not in self.data:
            return 0
        removed = 0
        to_remove = []
        for m, score in self.data[key].items():
            if min_val == "-inf":
                min_f = -float('inf')
            else:
                min_f = float(min_val)
            if max_val == "+inf":
                max_f = float('inf')
            else:
                max_f = float(max_val)
            if min_f <= score <= max_f:
                to_remove.append(m)
        for m in to_remove:
            self.data[key].pop(m, None)
            removed += 1
        return removed

    def zrangebyscore(self, key, min_val, max_val):
        if key not in self.data:
            return []
        results = []
        for m, score in self.data[key].items():
            if min_val == "-inf":
                min_f = -float('inf')
            else:
                min_f = float(min_val)
            if max_val == "+inf":
                max_f = float('inf')
            else:
                max_f = float(max_val)
            if min_f <= score <= max_f:
                results.append(str(m).encode('utf-8'))
        return results

    def zscore(self, key, member):
        if key in self.data:
            return self.data[key].get(member, None)
        return None

    def zrem(self, key, *members):
        if key not in self.data:
            return 0
        removed = 0
        for m in members:
            if m in self.data[key]:
                self.data[key].pop(m)
                removed += 1
        return removed

    def hincrby(self, key, field, amount):
        if key not in self.data:
            self.data[key] = {}
        val = int(self.data[key].get(field, 0))
        new_val = val + amount
        self.data[key][field] = str(new_val)
        return new_val

    def hget(self, key, field):
        if key in self.data:
            val = self.data[key].get(field, None)
            return val.encode('utf-8') if (val is not None and isinstance(val, str)) else val
        return None

    def hset(self, key, field=None, value=None, mapping=None):
        if key not in self.data:
            self.data[key] = {}
        if mapping:
            for f, v in mapping.items():
                self.data[key][f] = str(v)
            return len(mapping)
        else:
            self.data[key][field] = str(value)
            return 1

    def hmget(self, key, fields):
        results = []
        for f in fields:
            val = self.data[key].get(f, None) if key in self.data else None
            results.append(val.encode('utf-8') if (val is not None and isinstance(val, str)) else val)
        return results

    def incr(self, key):
        val = int(self.data.get(key, 0))
        new_val = val + 1
        self.data[key] = str(new_val)
        return new_val

    def expire(self, key, seconds):
        self.expirations[key] = seconds
        return True

    def set(self, key, value, ex=None, px=None, nx=False, xx=False):
        if nx and key in self.data:
            return None
        if xx and key not in self.data:
            return None
        self.data[key] = str(value)
        if ex:
            self.expirations[key] = ex
        return True

    def pipeline(self):
        return MockRedisPipeline(self)

try:
    if IS_TESTING:
        # Connect to real Redis db 15 if running, otherwise use MockRedis fallback
        try:
            redis_pool = redis.ConnectionPool.from_url(
                getattr(settings, 'REDIS_URL', 'redis://127.0.0.1:6379/15'),
                max_connections=5
            )
            redis_client = redis.StrictRedis(connection_pool=redis_pool)
            redis_client.ping()
            redis_client.flushdb()
            REDIS_AVAILABLE = True
        except Exception as e:
            logger.warning(f"Could not connect to Redis for tests. Using MockRedis fallback: {e}")
            redis_client = MockRedis()
            REDIS_AVAILABLE = True
    else:
        redis_pool = redis.ConnectionPool.from_url(
            getattr(settings, 'REDIS_URL', 'redis://127.0.0.1:6379/0'),
            max_connections=50
        )
        redis_client = redis.StrictRedis(connection_pool=redis_pool)
        # Ping to check connectivity
        redis_client.ping()
        REDIS_AVAILABLE = True
except Exception as e:
    logger.warning(f"Redis server is offline or unavailable. Falling back to database: {e}")
    REDIS_AVAILABLE = False
    redis_client = None

class RedisKeys:
    @staticmethod
    def feed(user_id):
        return f"feed:user:{user_id}"
    
    @staticmethod
    def user_stats(user_id):
        return f"user:{user_id}:stats"
    
    @staticmethod
    def post_stats(post_id):
        return f"post:{post_id}:stats"
    
    @staticmethod
    def unread_notifications(user_id):
        return f"user:{user_id}:unread_notifications"
    
    @staticmethod
    def trending_posts():
        return "trending_posts"
    
    @staticmethod
    def rate_limit(user_id, prefix="api"):
        import time
        minute = int(time.time() // 60)
        return f"rate_limit:{prefix}:{user_id}:{minute}"

# Stats caching helpers
def increment_like_count(post_id, amount=1):
    if not REDIS_AVAILABLE:
        return 0
    try:
        key = RedisKeys.post_stats(post_id)
        new_val = redis_client.hincrby(key, "likes_count", amount)
        redis_client.zincrby(RedisKeys.trending_posts(), amount, post_id)
        return new_val
    except Exception as e:
        logger.error(f"Redis connection error during increment_like_count: {e}")
        return 0

def get_like_count(post_id, fallback_func):
    if not REDIS_AVAILABLE:
        return fallback_func()
    try:
        key = RedisKeys.post_stats(post_id)
        val = redis_client.hget(key, "likes_count")
        if val is not None:
            return int(val)
    except Exception as e:
        logger.error(f"Redis connection error during get_like_count: {e}")
    
    count = fallback_func()
    try:
        redis_client.hset(key, "likes_count", count)
    except Exception as e:
        pass
    return count

def increment_follower_stats(user_id, following_id, amount=1):
    if not REDIS_AVAILABLE:
        return
    try:
        redis_client.hincrby(RedisKeys.user_stats(user_id), "following_count", amount)
        redis_client.hincrby(RedisKeys.user_stats(following_id), "followers_count", amount)
    except Exception as e:
        logger.error(f"Redis connection error during increment_follower_stats: {e}")

def get_user_stats(user_id, fallback_func):
    """
    Returns (followers_count, following_count) from cache or DB fallback.
    """
    if not REDIS_AVAILABLE:
        return fallback_func()
    try:
        key = RedisKeys.user_stats(user_id)
        stats = redis_client.hmget(key, ["followers_count", "following_count"])
        if stats[0] is not None and stats[1] is not None:
            return int(stats[0]), int(stats[1])
    except Exception as e:
        logger.error(f"Redis connection error during get_user_stats: {e}")
    
    followers, following = fallback_func()
    try:
        redis_client.hset(key, mapping={
            "followers_count": followers,
            "following_count": following
        })
    except Exception as e:
        pass
    return followers, following

def get_cached_feed(user_id, page=1, page_size=5):
    if not REDIS_AVAILABLE:
        return []
    try:
        key = RedisKeys.feed(user_id)
        start = (page - 1) * page_size
        end = start + page_size - 1
        post_ids = redis_client.zrevrange(key, start, end)
        return [int(pid) for pid in post_ids]
    except Exception as e:
        logger.error(f"Redis connection error during get_cached_feed: {e}")
        return []

def check_rate_limit(user_id, limit=60, prefix="api"):
    if not REDIS_AVAILABLE:
        return True
    try:
        key = RedisKeys.rate_limit(user_id, prefix)
        current = redis_client.incr(key)
        if current == 1:
            redis_client.expire(key, 60)
        return current <= limit
    except Exception as e:
        logger.error(f"Redis connection error during check_rate_limit: {e}")
        return True
