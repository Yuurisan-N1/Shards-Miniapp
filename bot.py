import os
import re
import sys
import json
import time
import calendar
import signal
import asyncio
import urllib.parse
import aiohttp

from utils.banner import show_banner

RESET  = "\033[0m"
BOLD   = "\033[1m"
RED    = "\033[91m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"

MY_PROJECT = "ShardsEarn Miniapp"
BASE_URL   = "https://shardsearn.site"
REF_CODE   = "6004380466"

AD_DWELL_SECONDS = 12
ADS_TOKEN_ATTEMPTS = 4
ADS_RETRY_SECONDS = 4
CAPTCHA_ATTEMPTS = 5
CAPTCHA_RETRY_SECONDS = 3
TASK_RETRY_SECONDS = 3
DIRECT_DWELL_MS = 8000
TTT_MOVE_DELAY = 1

BANNED_CODES = (
    91, 93, 124, 35, 33, 64, 36, 37, 94, 38, 42, 40, 41,
    45, 44, 58, 59, 39, 34, 96, 126, 43, 61, 60, 62, 63, 47, 92,
)
BANNED_CHARS = tuple(chr(code) for code in BANNED_CODES)

HEADERS_BASE = {
    "accept": "*/*",
    "accept-encoding": "identity",
    "accept-language": "en-US,en;q=0.9",
    "cache-control": "no-cache",
    "content-type": "application/json",
    "origin": BASE_URL,
    "pragma": "no-cache",
    "priority": "u=1, i",
    "referer": f"{BASE_URL}/?tgWebAppStartParam={REF_CODE}",
    "sec-ch-ua": '"Chromium";v="152", "Google Chrome";v="152", "Not?A_Brand";v="24"',
    "sec-ch-ua-mobile": "?1",
    "sec-ch-ua-platform": '"Android"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "user-agent": "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Mobile Safari/537.36",
    "csv": "10",
}

CHEST_STATE = {}


def log_green(msg):
    print(f"{GREEN}{BOLD}{msg}{RESET}")


def log_yellow(msg):
    print(f"{YELLOW}{BOLD}{msg}{RESET}")


def log_red(msg):
    print(f"{RED}{BOLD}{msg}{RESET}")


def signal_handler(sig, frame):
    print()
    log_red("Script stopped by user")
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)


def load_config():
    defaults = {"settings": {"sleep_seconds": 3600}}
    if not os.path.exists("config.json"):
        return defaults
    try:
        with open("config.json") as f:
            return json.load(f)
    except Exception:
        return defaults


def load_data():
    if not os.path.exists("data.txt"):
        log_red("File data.txt was not found")
        sys.exit(1)
    lines = [l.strip() for l in open("data.txt").readlines() if l.strip() and not l.strip().startswith("#")]
    if not lines:
        log_red("File data.txt is empty")
        sys.exit(1)
    return lines


def load_proxies():
    if not os.path.exists("proxy.txt"):
        return []
    try:
        return [l.strip() for l in open("proxy.txt").readlines() if l.strip() and not l.strip().startswith("#")]
    except Exception:
        return []


def get_proxy(proxies, idx):
    if not proxies:
        return None
    return proxies[idx % len(proxies)]


def normalize_proxy(proxy_line):
    if not proxy_line:
        return None
    value = proxy_line.strip()
    if "://" in value:
        return value
    parts = value.split(":")
    if len(parts) == 4:
        host, port, user, password = parts
        return f"http://{user}:{password}@{host}:{port}"
    if len(parts) == 3:
        host, port, user = parts
        return f"http://{user}@{host}:{port}"
    return f"http://{value}"


def mask_proxy(proxy_url):
    try:
        value = proxy_url.split("://")[-1]
        after_at = value.split("@")[-1]
        host_part = after_at.split(":")[0]
        port_part = after_at.split(":")[1] if ":" in after_at else ""
        octets = host_part.split(".")
        if len(octets) == 4:
            masked_host = f"{octets[0]}*****{octets[3]}"
        elif len(host_part) > 4:
            masked_host = f"{host_part[:2]}*****{host_part[-2:]}"
        else:
            masked_host = "***"
        suffix = f":{port_part}" if port_part else ""
        return f"http://user:pass@{masked_host}{suffix}"
    except Exception:
        return "http://user:pass@***:***"


def clean_text(value, fallback):
    text = str(value)
    for symbol in BANNED_CHARS:
        text = text.replace(symbol, " ")
    text = " ".join(text.split())
    return text if text else str(fallback)


def parse_init_data(init_data):
    try:
        parsed = dict(urllib.parse.parse_qsl(init_data))
        return json.loads(parsed.get("user", "{}"))
    except Exception:
        return {}


def parse_start_param(init_data):
    try:
        return dict(urllib.parse.parse_qsl(init_data)).get("start_param") or ""
    except Exception:
        return ""


def format_duration(seconds):
    try:
        seconds = int(seconds)
    except Exception:
        return "an unknown amount of time"
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    rest = seconds % 60
    if hours > 0:
        return f"{hours} hours {minutes} minutes"
    if minutes > 0:
        return f"{minutes} minutes {rest} seconds"
    return f"{rest} seconds"


def timestamp_of(value):
    if not value:
        return None
    try:
        text = str(value).replace("Z", "").split(".")[0]
        return calendar.timegm(time.strptime(text, "%Y-%m-%dT%H:%M:%S"))
    except Exception:
        return None


def seconds_until_iso(value):
    target = timestamp_of(value)
    if target is None:
        return 0
    return int(target - time.time())


def iso_gap(start_value, end_value):
    start = timestamp_of(start_value)
    end = timestamp_of(end_value)
    if start is None or end is None:
        return 0
    return max(0, int(end - start))


def countdown(seconds):
    for remaining in range(int(seconds), 0, -1):
        h = remaining // 3600
        m = (remaining % 3600) // 60
        s = remaining % 60
        print(f"\r{YELLOW}{BOLD}Next cycle starts in {h:02d}:{m:02d}:{s:02d}{RESET}", end="", flush=True)
        time.sleep(1)
    print()


def remaining_budget(deadline):
    return int(deadline - time.time())


async def api(session, method, endpoint, payload=None, proxy=None):
    try:
        async with session.request(
            method,
            f"{BASE_URL}{endpoint}",
            headers=HEADERS_BASE,
            json=payload,
            proxy=proxy,
            timeout=aiohttp.ClientTimeout(total=30),
        ) as r:
            raw = await r.read()
            try:
                data = json.loads(raw)
            except Exception:
                data = None
            return r.status, data
    except Exception as e:
        log_red(f"Request to {clean_text(endpoint, 'endpoint')} failed with {clean_text(type(e).__name__, 'Error')}")
        return None, None


async def api_get_svg(session, endpoint, params, proxy):
    try:
        async with session.get(
            f"{BASE_URL}{endpoint}",
            params=params,
            headers=HEADERS_BASE,
            proxy=proxy,
            timeout=aiohttp.ClientTimeout(total=30),
        ) as r:
            if r.status != 200:
                return ""
            return await r.text()
    except Exception:
        return ""


def svg_shape(svg):
    try:
        shapes = re.findall(r'<path[^>]*?\bd="([^"]+)"', svg or "")
        return frozenset("".join(shape.split()) for shape in shapes)
    except Exception:
        return frozenset()


def board_cells(value):
    if isinstance(value, dict):
        value = value.get("board")
    if not isinstance(value, list):
        return [""] * 9
    cells = [str(cell or "") for cell in value][:9]
    while len(cells) < 9:
        cells.append("")
    return cells


def ad_provider(task):
    kind = str((task or {}).get("type") or "").strip().lower()
    if not kind:
        return "adsgram"
    return kind.split("_")[0] or "adsgram"


def is_ad_task(task):
    return bool(task.get("isMultiView") and task.get("viewRewards"))


def board_winner(board):
    lines = ((0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 3, 6), (1, 4, 7), (2, 5, 8), (0, 4, 8), (2, 4, 6))
    for a, b, c in lines:
        if board[a] and board[a] == board[b] and board[a] == board[c]:
            return board[a]
    return None


def minimax(board, turn, me, opp, depth):
    winner = board_winner(board)
    if winner == me:
        return 10 - depth
    if winner == opp:
        return depth - 10
    if all(board):
        return 0
    best = None
    for index in range(9):
        if board[index]:
            continue
        board[index] = turn
        score = minimax(board, opp if turn == me else me, me, opp, depth + 1)
        board[index] = ""
        if best is None or (turn == me and score > best) or (turn == opp and score < best):
            best = score
    return best


def best_move(board, me="O"):
    opp = "X" if me == "O" else "O"
    best = None
    choice = None
    for index in range(9):
        if board[index]:
            continue
        board[index] = me
        score = minimax(board, opp, me, opp, 1)
        board[index] = ""
        if best is None or score > best:
            best = score
            choice = index
    return choice


class AdsClient:
    def __init__(self, session, proxy):
        self.session = session
        self.proxy = proxy
        self.ads_before_captcha = 0
        self.remaining = 0
        self.exhausted = False

    async def captcha_status(self):
        code, status = await api(self.session, "GET", "/api/captcha/status", None, self.proxy)
        if code == 200 and status:
            self.ads_before_captcha = int(status.get("adsBeforeCaptcha") or self.ads_before_captcha or 3)
            since = int(status.get("adsSinceCaptcha") or 0)
            if status.get("owesCaptcha") or status.get("locked"):
                self.remaining = 0
            else:
                self.remaining = max(0, self.ads_before_captcha - since)
            return status
        return None

    async def solve_captcha(self):
        for _ in range(CAPTCHA_ATTEMPTS):
            code, challenge = await api(self.session, "POST", "/api/captcha/new", {}, self.proxy)
            if not (code == 200 and challenge and challenge.get("ok")):
                await asyncio.sleep(CAPTCHA_RETRY_SECONDS)
                continue
            target_shape = svg_shape(await api_get_svg(self.session, "/api/captcha/img", {"token": challenge.get("target")}, self.proxy))
            options = challenge.get("options") or []
            picked = None
            for index, token in enumerate(options):
                option_shape = svg_shape(await api_get_svg(self.session, "/api/captcha/img", {"token": token}, self.proxy))
                if target_shape and option_shape and (target_shape <= option_shape or option_shape <= target_shape):
                    picked = index
                    break
            if picked is None:
                await asyncio.sleep(CAPTCHA_RETRY_SECONDS)
                continue
            code, graded = await api(
                self.session,
                "POST",
                "/api/captcha/grade",
                {"id": challenge.get("id"), "token": options[picked], "purpose": "ad"},
                self.proxy,
            )
            if code == 200 and graded and graded.get("correct"):
                self.remaining = self.ads_before_captcha or 3
                return True
            if graded and graded.get("locked"):
                return False
            await asyncio.sleep(CAPTCHA_RETRY_SECONDS)
        return False

    async def ensure_ready(self):
        await self.captcha_status()
        if self.remaining > 0:
            return True
        return await self.solve_captcha()

    async def cancel_token(self, token, reason):
        if not token:
            return
        await api(self.session, "POST", "/api/ads/cancel-token", {"token": token, "reason": reason}, self.proxy)

    def is_limited(self, response):
        if not response:
            return False
        text = str(response.get("error") or "").lower()
        return "hourly" in text or "reward limit" in text

    async def serve_ad(self, provider=None, task_id=None):
        if self.exhausted:
            return None
        if not await self.ensure_ready():
            log_red("Verification challenge could not be solved so the ad flow was paused")
            return None
        payload = {"provider": provider or "adsgram"}
        if task_id:
            payload["taskId"] = task_id
        for _ in range(ADS_TOKEN_ATTEMPTS):
            code, issued = await api(self.session, "POST", "/api/ads/generate-token", payload, self.proxy)
            if code == 200 and issued and issued.get("token"):
                token = issued.get("token")
                self.remaining -= 1
                await asyncio.sleep(AD_DWELL_SECONDS)
                body = {
                    "token": token,
                    "clickData": {"requests": 1, "timestamp": int(time.time() * 1000)},
                    "adFlow": {"adsOffered": 1, "adsShown": 1, "adsClicked": 1},
                }
                mark_code, marked = await api(self.session, "POST", "/api/ads/mark-clicked", body, self.proxy)
                if mark_code == 200 and marked and marked.get("credited") is not None:
                    return marked
                if marked and marked.get("error") == "CAPTCHA_REQUIRED":
                    await self.cancel_token(token, "error")
                    self.remaining = 0
                    if await self.ensure_ready():
                        continue
                    return None
                if self.is_limited(marked):
                    await self.cancel_token(token, "error")
                    self.exhausted = True
                    log_yellow("Ad rewards for this account are limited by the server for the current hour and the limit was reached")
                    return None
                await self.cancel_token(token, "ad_not_completed")
                if mark_code == 429:
                    await asyncio.sleep(ADS_RETRY_SECONDS)
                    continue
                return None
            if self.is_limited(issued):
                self.exhausted = True
                log_yellow("Ad rewards for this account are limited by the server for the current hour and the limit was reached")
                return None
            wait = 5
            if issued:
                try:
                    wait = int(issued.get("waitSeconds") or 5)
                except Exception:
                    wait = 5
            await asyncio.sleep(wait + 2)
        return None


async def login(session, init_data, proxy):
    code, resp = await api(session, "POST", "/api/auth/telegram/initdata", {"initData": init_data}, proxy)
    if code != 200 or not resp or not resp.get("ok"):
        return None
    return resp.get("user") or None


async def watch_ad_views(session, ads, task, proxy):
    progress = task.get("viewProgress") or {}
    remaining = int(progress.get("viewsRemaining") or 0)
    max_views = int(progress.get("maxViews") or 0)
    label = clean_text(task.get("title") or "Ad task", "Ad task")
    if remaining <= 0:
        return 0
    claimed = 0
    for _ in range(remaining):
        view = await ads.serve_ad(ad_provider(task), task.get("id"))
        if not view:
            break
        claimed += 1
        left = view.get("viewsRemaining")
        log_green(f"Ad view for {clean_text(label, 'Ad task')} was watched and credited {clean_text(view.get('credited'), 0)} shards")
        if left is None or int(left) <= 0:
            break
        await asyncio.sleep(ADS_RETRY_SECONDS)
    if claimed > 0:
        log_green(f"Ad rewards for {clean_text(label, 'Ad task')} were claimed and {clean_text(claimed, 0)} views were credited")
    elif not ads.exhausted:
        log_yellow(f"Ad reward for {clean_text(label, 'Ad task')} could not be verified because the ad network served no advertisement")
    return claimed


async def run_earn_page(session, ads, proxy):
    code, page = await api(session, "GET", "/api/pages/earn", None, proxy)
    if code != 200 or not page:
        log_red("Task list could not be retrieved")
        return
    tasks = [task for task in (page.get("tasks") or []) if task.get("isActive") is not False]

    for task in tasks:
        if is_ad_task(task):
            await watch_ad_views(session, ads, task, proxy)

    claimed = 0
    verified = 0
    pending = 0
    for task in tasks:
        if is_ad_task(task):
            continue
        if task.get("completionStatus") == "approved":
            continue
        code, resp = await api(session, "POST", "/api/tasks/complete", {"taskId": task.get("id")}, proxy)
        if code == 200 and resp and resp.get("ok"):
            completion = resp.get("completion") or {}
            if completion.get("status") == "approved":
                claimed += 1
            else:
                verified += 1
        else:
            error_code = (resp or {}).get("errorCode")
            error_text = (resp or {}).get("error") or ""
            if error_code == "BOT_NOT_ADMIN" or "not an administrator" in error_text:
                pending += 1
            elif "already completed" in error_text:
                continue
            elif (resp or {}).get("needsRetry") or error_code == "NOT_MEMBER":
                verified += 1
            else:
                pending += 1
        await asyncio.sleep(TASK_RETRY_SECONDS)

    if claimed > 0:
        log_green(f"All available tasks were completed and {clean_text(claimed, 0)} rewards were claimed")
    elif verified > 0:
        log_yellow(f"{clean_text(verified, 0)} account tasks are still being verified by the server")
    elif pending > 0:
        log_yellow(f"{clean_text(pending, 0)} account tasks could not be completed on this run")
    else:
        log_green("Every available account task was already completed")


async def run_earn_more(session, ads, proxy, deadline):
    code, status = await api(session, "GET", "/api/earn-more/status", None, proxy)
    if code != 200 or not status:
        log_red("Earn more status could not be retrieved")
        return
    total = int(status.get("totalSteps") or 0)
    step = status.get("step")
    if step is None or step >= total:
        log_green("Earn more rewards were already fully claimed for this account")
        return

    claimed = 0
    current = step
    while remaining_budget(deadline) > 60:
        code, status = await api(session, "GET", "/api/earn-more/status", None, proxy)
        if code != 200 or not status:
            break
        current = status.get("step")
        total = int(status.get("totalSteps") or 0)
        if current is None or current >= total:
            break
        paused = False
        for key in ("cooldownUntil", "penaltyUntil"):
            value = seconds_until_iso(status.get(key))
            if value > 0:
                if value > remaining_budget(deadline):
                    log_yellow(f"Earn more progress is {clean_text(current, 0)} out of {clean_text(total, 0)} steps and {clean_text(claimed, 0)} rewards were claimed")
                    return
                await asyncio.sleep(value + 2)
                paused = True
        if paused:
            continue
        rewards = {}
        for item in status.get("rewards") or []:
            rewards[item.get("step")] = item
        reward = rewards.get(current) or {}
        provider = str(reward.get("ad") or "").strip().lower()
        body = {"step": current}
        if provider == "direct":
            body["dwellSeconds"] = DIRECT_DWELL_MS
            body["clicked"] = True
        else:
            view = await ads.serve_ad(provider or None)
            if not view:
                break
            body["adsOffered"] = 1
            body["adsShown"] = 1
            body["adsClicked"] = 1
        code, resp = await api(session, "POST", "/api/earn-more/claim", body, proxy)
        if code == 200 and resp and resp.get("ok"):
            claimed += 1
            log_green(f"Earn more step {clean_text(current, 0)} was claimed and credited {clean_text(resp.get('reward', 0), 0)} shards")
            continue
        if resp and seconds_until_iso(resp.get("cooldownUntil")) > 0:
            continue
        break

    log_green(f"Earn more progress is {clean_text(current, 0)} out of {clean_text(total, 0)} steps and {clean_text(claimed, 0)} rewards were claimed")


async def run_lucky_chest(session, ads, proxy):
    code, page = await api(session, "GET", "/api/pages/play", None, proxy)
    if code != 200 or not page:
        log_red("Play page could not be retrieved")
        return
    user = page.get("user") or {}
    points = int(user.get("points") or 0)
    account_key = str(user.get("id") or user.get("tgUserId") or "default")

    if user.get("hasActiveChest"):
        view = await ads.serve_ad()
        if not view:
            if not ads.exhausted:
                log_yellow("Lucky chest reward could not be opened because the ad network served no advertisement")
            return
        code, resp = await api(session, "POST", "/api/play/chest/claim", {"shardChosen": 0}, proxy)
        if code == 200 and resp and resp.get("ok"):
            log_green(f"Lucky chest reward was claimed and credited {clean_text(resp.get('finalReward', 0), 0)} shards with a bonus of {clean_text(resp.get('bonusPercent', 0), 0)} percent")
        else:
            reason = (resp or {}).get("error") or "the server refused the request"
            log_yellow(f"Lucky chest reward could not be claimed on this run because {clean_text(reason, 'the server refused the request')}")
        return

    cooldown = CHEST_STATE.get(account_key, {}).get("cooldown") or 0
    elapsed = -seconds_until_iso(user.get("lastChestAt")) if user.get("lastChestAt") else 0
    if cooldown and user.get("lastChestAt") and elapsed < cooldown:
        log_yellow(f"Lucky chest is still locked for {clean_text(format_duration(cooldown - elapsed), 'a while')}")
        return

    purchase_view = await ads.serve_ad()
    if not purchase_view:
        if not ads.exhausted:
            log_yellow("Lucky chest could not be purchased because the ad network served no advertisement")
        return
    code, resp = await api(session, "POST", "/api/play/chest/purchase", {}, proxy)
    if not (code == 200 and resp and resp.get("ok")):
        end = (resp or {}).get("cooldownEnd")
        learned = iso_gap(user.get("lastChestAt"), end) if end and user.get("lastChestAt") else 0
        if learned:
            CHEST_STATE[account_key] = {"cooldown": learned}
        reason = (resp or {}).get("error") or "the server refused the request"
        log_yellow(f"Lucky chest could not be purchased on this run because {clean_text(reason, 'the server refused the request')}")
        return
    paid = points - int(resp.get("newBalance") if resp.get("newBalance") is not None else points)
    log_green(f"Lucky chest was purchased for {clean_text(paid, 0)} shards")

    open_view = await ads.serve_ad()
    if not open_view:
        if not ads.exhausted:
            log_yellow("Lucky chest could not be opened because the ad network served no advertisement")
        return
    code, resp = await api(session, "POST", "/api/play/chest/claim", {"shardChosen": 0}, proxy)
    if code == 200 and resp and resp.get("ok"):
        log_green(f"Lucky chest was opened and credited {clean_text(resp.get('finalReward', 0), 0)} shards with a bonus of {clean_text(resp.get('bonusPercent', 0), 0)} percent")
    else:
        reason = (resp or {}).get("error") or "the server refused the request"
        log_yellow(f"Lucky chest was opened but the reward could not be claimed on this run because {clean_text(reason, 'the server refused the request')}")


async def play_out_game(session, proxy, game_id, board):
    result = None
    while True:
        move = best_move(board)
        if move is None:
            break
        code, moved = await api(session, "POST", "/api/tictactoe/move", {"gameId": game_id, "humanMove": move}, proxy)
        if not (code == 200 and moved and moved.get("ok")):
            break
        board = board_cells(moved.get("boardState"))
        if moved.get("gameOver"):
            result = moved
            break
        await asyncio.sleep(TTT_MOVE_DELAY)
    return result


async def claim_game(session, ads, proxy, game_id, result):
    view = await ads.serve_ad()
    if not view:
        if not ads.exhausted:
            log_yellow("Tic tac toe reward is waiting and could not be claimed because the ad network served no advertisement")
        return False
    code, claim = await api(session, "POST", "/api/tictactoe/claim", {"gameId": game_id}, proxy)
    if not (code == 200 and claim and claim.get("ok")):
        log_yellow("Tic tac toe reward could not be claimed on this run")
        return False
    outcome = claim.get("outcome") or claim.get("winner") or (result or {}).get("winner") or "draw"
    paid = claim.get("finalReward")
    if paid is None:
        paid = claim.get("rewardPaid")
    log_green(f"Tic tac toe game ended with a {clean_text(outcome, 'draw')} and {clean_text(paid, 0)} shards were paid")
    return True


async def load_play_state(session, proxy):
    code, page = await api(session, "GET", "/api/pages/play", None, proxy)
    if code != 200 or not page:
        return None, None
    return page.get("user") or {}, page.get("tictactoe") or {}


async def resume_game(session, ads, proxy, game_id, board):
    result = await play_out_game(session, proxy, game_id, board_cells(board))
    if result is None:
        log_yellow("Tic tac toe game was left unfinished because the opponent did not respond")
        return
    await claim_game(session, ads, proxy, game_id, result)


async def run_tictactoe(session, ads, proxy, deadline):
    user, state = await load_play_state(session, proxy)
    if user is None:
        log_red("Play page could not be retrieved")
        return

    unclaimed = state.get("unclaimedGame") or {}
    active = state.get("activeGame") or {}

    if unclaimed.get("gameId") or unclaimed.get("id"):
        await claim_game(session, ads, proxy, unclaimed.get("gameId") or unclaimed.get("id"), unclaimed)
        return

    if active.get("gameId") or active.get("id"):
        await resume_game(session, ads, proxy, active.get("gameId") or active.get("id"), active.get("boardState"))
        return

    while remaining_budget(deadline) > 60:
        if state.get("dailyLimitReached"):
            log_yellow(f"Tic tac toe daily limit of {clean_text(state.get('maxGames', 0), 0)} games was reached")
            return
        if state.get("canPlay") is False:
            log_yellow(f"Tic tac toe is still cooling down for {clean_text(format_duration(state.get('cooldownSeconds', 0)), 'a while')}")
            return

        points = int(user.get("points") or 0)
        view = await ads.serve_ad()
        if not view:
            if not ads.exhausted:
                log_yellow("Tic tac toe game could not be started because the ad network served no advertisement")
            return
        code, started = await api(session, "POST", "/api/tictactoe/start", {}, proxy)
        if not (code == 200 and started and started.get("gameId")):
            if started and started.get("errorCode") == "COOLDOWN":
                log_yellow(f"Tic tac toe is still cooling down for {clean_text(format_duration(started.get('remainingSeconds', 0)), 'a while')}")
                return
            reason = (started or {}).get("error") or "the server refused the request"
            log_yellow(f"Tic tac toe game could not be started on this run because {clean_text(reason, 'the server refused the request')}")
            return

        game_id = started.get("gameId")
        new_balance = started.get("newBalance")
        stake = points - int(new_balance) if new_balance is not None else 0
        log_green(f"Tic tac toe game was started with a stake of {clean_text(stake, 0)} shards")

        result = await play_out_game(session, proxy, game_id, board_cells(started.get("boardState")))
        if result is None:
            log_yellow("Tic tac toe game was left unfinished because the opponent did not respond")
            return
        if not await claim_game(session, ads, proxy, game_id, result):
            return

        user, state = await load_play_state(session, proxy)
        if user is None:
            return


async def process_account(init_data, proxy, index, budget_seconds):
    user_info = parse_init_data(init_data)
    if not user_info.get("id"):
        log_red(f"Account on line {clean_text(index, 0)} holds invalid initData and was skipped")
        return

    start_param = parse_start_param(init_data)
    if not start_param:
        log_yellow(f"Account on line {clean_text(index, 0)} holds no start parameter so it carries no referral binding")
    elif start_param != REF_CODE:
        log_yellow(f"Account on line {clean_text(index, 0)} was referred by {clean_text(start_param, 'another account')} instead of {clean_text(REF_CODE, 'the configured code')}")

    connector = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        user = await login(session, init_data, proxy)
        if not user:
            log_red("Login failed for this account")
            return

        name = clean_text(user.get("tgUsername") or user.get("tgFirstName") or "Unknown", "Unknown")
        log_green(f"Account {clean_text(name, 'Unknown')} loaded successfully")

        code, dashboard = await api(session, "GET", "/api/pages/dashboard", None, proxy)
        if code != 200 or not dashboard:
            log_red("Account statistics could not be retrieved")
            return

        state = dashboard.get("user") or {}
        stats = dashboard.get("stats") or {}
        log_green(f"total balance is {clean_text(state.get('points', 0), 0)} shards")
        log_yellow(f"Rank {clean_text(stats.get('rank', 0), 0)} out of {clean_text(stats.get('totalUsers', 0), 0)} participants with {clean_text(stats.get('referrals', 0), 0)} referrals")

        ads = AdsClient(session, proxy)
        await ads.captcha_status()
        deadline = time.time() + budget_seconds

        await run_earn_page(session, ads, proxy)
        await run_earn_more(session, ads, proxy, deadline)
        await run_lucky_chest(session, ads, proxy)
        await run_tictactoe(session, ads, proxy, deadline)

        code, final_user = await api(session, "GET", "/api/auth/me", None, proxy)
        if code == 200 and final_user and final_user.get("user"):
            balance = final_user.get("user") or {}
            log_green(f"Final balance is {clean_text(balance.get('points', 0), 0)} shards")


async def main_async(accounts, proxies, sleep_secs):
    cycle = 1
    while True:
        log_yellow(f"Starting automation cycle number {clean_text(cycle, 0)}")

        for idx, init_data in enumerate(accounts):
            if idx > 0:
                print()

            proxy_line = get_proxy(proxies, idx)
            proxy_url = normalize_proxy(proxy_line) if proxy_line else None
            if proxy_url:
                log_yellow(f"Using proxy {mask_proxy(proxy_url)}")

            await process_account(init_data, proxy_url, idx + 1, max(60, int(sleep_secs) // 4))

        log_yellow(f"Automation cycle number {clean_text(cycle, 0)} is complete and all accounts were processed")
        cycle += 1
        countdown(sleep_secs)
        show_banner(MY_PROJECT)


def main():
    show_banner(MY_PROJECT)

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    config = load_config()
    sleep_secs = config.get("settings", {}).get("sleep_seconds", 3600)
    accounts = load_data()
    proxies = load_proxies()
    asyncio.run(main_async(accounts, proxies, sleep_secs))


if __name__ == "__main__":
    main()
