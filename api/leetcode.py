import aiohttp
from typing import Optional
import asyncio

LEETCODE_GRAPHQL_URL = "https://leetcode.com/graphql"

# GraphQL query for user profile stats
STATS_QUERY = """
query getUserProfile($username: String!) {
  matchedUser(username: $username) {
    username
    profile {
      realName
      ranking
    }
    submitStatsGlobal {
      acSubmissionNum {
        difficulty
        count
      }
    }
  }
}
"""

# GraphQL query for recent accepted submissions
RECENT_SUBMISSIONS_QUERY = """
query getRecentSubmissions($username: String!, $limit: Int!) {
  recentAcSubmissionList(username: $username, limit: $limit) {
    id
    title
    titleSlug
    timestamp
  }
}
"""

HEADERS = {
    "Content-Type": "application/json",
    "Referer": "https://leetcode.com",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
}


class LeetCodeAPIError(Exception):
    """Raised when the LeetCode API returns an unexpected response."""
    pass


class LeetCodeClient:
    def __init__(self):
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(headers=HEADERS)
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def _post(self, query: str, variables: dict, retries: int = 3) -> dict:
        session = await self._get_session()
        payload = {"query": query, "variables": variables}

        for attempt in range(retries):
            try:
                async with session.post(
                    LEETCODE_GRAPHQL_URL, json=payload, timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status == 429:
                        wait = 2 ** attempt
                        await asyncio.sleep(wait)
                        continue
                    if resp.status != 200:
                        raise LeetCodeAPIError(f"HTTP {resp.status} from LeetCode API")
                    data = await resp.json()
                    if "errors" in data:
                        raise LeetCodeAPIError(f"GraphQL error: {data['errors']}")
                    return data
            except aiohttp.ClientError as e:
                if attempt == retries - 1:
                    raise LeetCodeAPIError(f"Network error after {retries} attempts: {e}")
                await asyncio.sleep(1)

        raise LeetCodeAPIError("Max retries exceeded")

    async def get_user_stats(self, username: str) -> dict:
        """
        Returns parsed stats for a LeetCode user:
        {
            "username": str,
            "real_name": str,
            "ranking": int,
            "total": int,
            "easy": int,
            "medium": int,
            "hard": int,
        }
        Raises LeetCodeAPIError if the user doesn't exist or is private.
        """
        data = await self._post(STATS_QUERY, {"username": username})
        user = data.get("data", {}).get("matchedUser")

        if not user:
            raise LeetCodeAPIError(f"User `{username}` not found or profile is private.")

        counts = {
            item["difficulty"]: item["count"]
            for item in user["submitStatsGlobal"]["acSubmissionNum"]
        }

        return {
            "username": user["username"],
            "real_name": user["profile"]["realName"] or username,
            "ranking": user["profile"]["ranking"],
            "total": counts.get("All", 0),
            "easy": counts.get("Easy", 0),
            "medium": counts.get("Medium", 0),
            "hard": counts.get("Hard", 0),
        }

    async def get_recent_submissions(self, username: str, limit: int = 20) -> list[dict]:
        """
        Returns a list of recent accepted submissions:
        [{"id": str, "title": str, "titleSlug": str, "timestamp": str}, ...]
        """
        data = await self._post(
            RECENT_SUBMISSIONS_QUERY, {"username": username, "limit": limit}
        )
        return data.get("data", {}).get("recentAcSubmissionList", [])


# Module-level singleton
leetcode = LeetCodeClient()