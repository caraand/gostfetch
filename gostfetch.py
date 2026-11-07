#!/usr/bin/env python3
"""gostfetch - CLI: слева лого дистра (из fastfetch), справа живой мониторинг.

Только stdlib (Python 3.11+ для чтения TOML-конфига). Для лого нужен fastfetch.

Запуск:   gostfetch            (или python3 gostfetch.py)
Опции:    --logo auto|none|ИМЯ|/путь/к/файлу.txt   (ИМЯ - любое лого fastfetch)
          --list-logos       вывести все доступные лого и выйти
          --refresh СЕК      скорость обновления (0.2 .. 10)
          --lang auto|ru|en  язык интерфейса
          --config ФАЙЛ      свой конфиг
          --distro ИМЯ       принудительно определить дистр
Клавиши:  q/Esc выход, +/- скорость, l/L следующее/предыдущее лого,
          g язык (ru/en), s сохранить в конфиг

Конфиг: $XDG_CONFIG_HOME/gostfetch/config.toml  (~/.config/gostfetch/config.toml)
    refresh = 1.0
    logo = "auto"
    lang = "auto"

Лого ищутся так (по порядку):
  1) путь, если в конфиге указан файл
  2) ~/.config/gostfetch/logos/<имя>.txt   (свои лого важнее)
  3) /usr/share/gostfetch/logos/<имя>.txt
  4) fastfetch: все встроенные лого; для auto он сам выбирает лого твоего дистра
  5) neofetch, если fastfetch нет
  6) простая заглушка с названием дистра
"""
import argparse
import curses
import glob
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
from collections import deque

try:
    import tomllib
except ImportError:  # Python < 3.11
    tomllib = None

__version__ = "0.3.0"
APP = "gostfetch"

HIST = 60
SPARK = "▁▂▃▄▅▆▇█"
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]|\x1b\][^\x07]*\x07")
SGR = re.compile(r"\x1b\[([0-9;]*)m")

# запасной цвет акцента, если достать цвет из самого лого не вышло
DISTROS = {
    "debian": curses.COLOR_RED,
    "fedora": curses.COLOR_BLUE,
    "arch": curses.COLOR_CYAN,
}
DEFAULT_COLOR = curses.COLOR_GREEN

LANGS = ("ru", "en")
REFRESH_STEPS = [0.25, 0.5, 1.0, 2.0, 5.0]
REFRESH_MIN, REFRESH_MAX = 0.2, 10.0
DEFAULTS = {"refresh": 1.0, "logo": "auto", "lang": "auto"}

SYSTEM_LOGO_DIRS = ["/usr/share/gostfetch/logos", "/usr/local/share/gostfetch/logos"]


# ───────────────────────── язык (ru / en) ─────────────────────────
STRINGS = {
    "ru": {
        "small_term": "Окно маловато, растяни терминал (min 50x18)",
        "no_gpu": "нет данных по загрузке (нужен nvidia-smi или amdgpu)",
        "help": "q выход  +/- скорость  l/L лого  g язык  s сохранить",
        "st_refresh": "обновление",
        "st_logo": "лого",
        "st_lang": "язык",
        "saved": "сохранено: {path}",
        "save_fail": "не удалось сохранить конфиг",
        "need_py311": "нужен Python 3.11+ для чтения конфига, использую дефолты",
        "cfg_bad": "конфиг {path} не прочитан ({err}), использую дефолты",
        "no_fastfetch": "fastfetch не найден, поставь его: из него берутся все лого",
        "hint1": "(поставь fastfetch —",
        "hint2": "будет настоящее лого)",
        "lbl_os": "ОС",
        "lbl_kernel": "Ядро",
        "lbl_host": "Хост",
        "lbl_uptime": "Аптайм",
        "cores": "ядра",
        "u_d": "д",
        "u_h": "ч",
        "u_m": "м",
        "sec": "с",
        "cfg_header": "конфиг gostfetch",
        "cfg_refresh": "refresh: секунды между обновлениями (0.2 .. 10)",
        "cfg_logo": "logo: auto | none | имя лого fastfetch (gostfetch --list-logos) | /путь/к/лого.txt",
        "cfg_lang": "lang: auto | ru | en",
        "a_desc": "лого дистра + живой мониторинг системы",
        "a_logo": "auto | none | имя лого fastfetch | путь к .txt (список: --list-logos)",
        "a_list": "вывести все доступные лого fastfetch и выйти",
        "a_refresh": "интервал обновления, сек ({lo}..{hi})",
        "a_lang": "язык интерфейса",
        "a_config": "путь к конфигу (по умолчанию XDG)",
        "a_distro": "принудительно задать дистр (для авто-лого)",
    },
    "en": {
        "small_term": "Terminal too small, resize it (min 50x18)",
        "no_gpu": "no load data (needs nvidia-smi or amdgpu)",
        "help": "q quit  +/- speed  l/L logo  g language  s save",
        "st_refresh": "refresh",
        "st_logo": "logo",
        "st_lang": "lang",
        "saved": "saved: {path}",
        "save_fail": "could not save config",
        "need_py311": "Python 3.11+ is required to read the config, using defaults",
        "cfg_bad": "config {path} could not be read ({err}), using defaults",
        "no_fastfetch": "fastfetch not found, install it: all logos come from it",
        "hint1": "(install fastfetch",
        "hint2": "for the real logo)",
        "lbl_os": "OS",
        "lbl_kernel": "Kernel",
        "lbl_host": "Host",
        "lbl_uptime": "Uptime",
        "cores": "cores",
        "u_d": "d",
        "u_h": "h",
        "u_m": "m",
        "sec": "s",
        "cfg_header": "gostfetch config",
        "cfg_refresh": "refresh: seconds between updates (0.2 .. 10)",
        "cfg_logo": "logo: auto | none | fastfetch logo name (gostfetch --list-logos) | /path/to/logo.txt",
        "cfg_lang": "lang: auto | ru | en",
        "a_desc": "distro logo + live system monitor",
        "a_logo": "auto | none | fastfetch logo name | path to .txt (list them: --list-logos)",
        "a_list": "print all available fastfetch logos and exit",
        "a_refresh": "refresh interval, seconds ({lo}..{hi})",
        "a_lang": "interface language",
        "a_config": "config path (XDG by default)",
        "a_distro": "force the distro (affects the auto logo)",
    },
}
_lang = "en"


def set_lang(code):
    global _lang
    _lang = code if code in LANGS else "en"


def t(key, **kw):
    s = STRINGS[_lang].get(key) or STRINGS["en"][key]
    return s.format(**kw) if kw else s


def detect_lang():
    """Язык системы по переменным окружения: ru* -> ru, всё остальное -> en."""
    for var in ("LC_ALL", "LC_MESSAGES", "LANGUAGE", "LANG"):
        v = os.environ.get(var, "")
        if v:
            return "ru" if v.lower().startswith("ru") else "en"
    return "en"


def resolve_lang(value):
    """auto | ru | en (и любой мусор) -> 'ru' или 'en'."""
    v = (value or "auto").strip().lower()
    return v if v in LANGS else detect_lang()


# ───────────────────────── конфиг ─────────────────────────
def config_dir():
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return os.path.join(base, APP)


def default_config_path():
    return os.path.join(config_dir(), "config.toml")


def clamp_refresh(v):
    try:
        return min(max(float(v), REFRESH_MIN), REFRESH_MAX)
    except (TypeError, ValueError):
        return DEFAULTS["refresh"]


def load_config(path):
    """-> (dict, warning|None). Любая ошибка = дефолты, программа не падает."""
    cfg = dict(DEFAULTS)
    if not os.path.exists(path):
        return cfg, None
    if tomllib is None:
        return cfg, t("need_py311")
    try:
        with open(path, "rb") as f:
            data = tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError) as e:
        return cfg, t("cfg_bad", path=path, err=e)
    if "refresh" in data:
        cfg["refresh"] = clamp_refresh(data["refresh"])
    if isinstance(data.get("logo"), str) and data["logo"].strip():
        cfg["logo"] = data["logo"].strip()
    lang = data.get("lang")
    if isinstance(lang, str) and lang.strip().lower() in ("auto", *LANGS):
        cfg["lang"] = lang.strip().lower()
    return cfg, None


def save_config(path, cfg):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"# {t('cfg_header')}\n")
            f.write(f"# {t('cfg_refresh')}\n")
            f.write(f"refresh = {cfg['refresh']:g}\n")
            f.write(f"# {t('cfg_logo')}\n")
            f.write(f"logo = {json.dumps(cfg['logo'], ensure_ascii=False)}\n")
            f.write(f"# {t('cfg_lang')}\n")
            f.write(f"lang = {json.dumps(cfg['lang'])}\n")
        return True
    except OSError:
        return False


# ───────────────────────── определение дистра ─────────────────────────
def read_os_release():
    data = {}
    for path in ("/etc/os-release", "/usr/lib/os-release"):
        try:
            with open(path) as f:
                for line in f:
                    if "=" in line:
                        k, v = line.rstrip().split("=", 1)
                        data[k] = v.strip('"')
            break
        except OSError:
            continue
    return data


def detect_distro(override=None):
    osr = read_os_release()
    pretty = osr.get("PRETTY_NAME", "Linux")
    if override:
        return override.lower(), pretty
    ids = [osr.get("ID", "").lower()] + osr.get("ID_LIKE", "").lower().split()
    for i in ids:
        if i in DISTROS:
            return i, pretty
        if i in ("ubuntu", "linuxmint", "raspbian", "pop"):
            return "debian", pretty
        if i in ("rhel", "centos"):
            return "fedora", pretty
        if i in ("manjaro", "endeavouros", "cachyos", "arcolinux"):
            return "arch", pretty
    return (ids[0] or "linux"), pretty


# ───────────────────────── лого ─────────────────────────
def run(cmd, timeout=2):
    try:
        # stdin закрыт, чтобы дочерний процесс не лез в терминал и не съедал клавиши curses;
        # encoding задан явно, чтобы юникод-лого не падали в C-локали
        r = subprocess.run(cmd, capture_output=True, encoding="utf-8", errors="replace",
                           timeout=timeout, stdin=subprocess.DEVNULL)
        return r.stdout if r.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def clean_logo(text):
    lines = [ANSI.sub("", l).rstrip() for l in text.splitlines()]
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    # убрать общий левый отступ
    pad = min((len(l) - len(l.lstrip()) for l in lines if l.strip()), default=0)
    return [l[pad:] for l in lines]


def read_logo_file(path):
    try:
        with open(path, encoding="utf-8") as f:
            lines = clean_logo(f.read())
        return lines or None
    except OSError:
        return None


def is_path(spec):
    return "/" in spec or spec.startswith("~") or spec.endswith(".txt")


def sgr_colors(raw):
    """Цвета переднего плана (номера xterm 0..255) из ANSI-вывода, по порядку появления."""
    for m in SGR.finditer(raw):
        p = [int(x) for x in m.group(1).split(";") if x.isdigit()]
        i = 0
        while i < len(p):
            c = p[i]
            if 30 <= c <= 37:
                yield c - 30
            elif 90 <= c <= 97:
                yield c - 90 + 8
            elif c == 38 and p[i + 1:i + 2] == [5] and i + 2 < len(p):
                yield p[i + 2]
                i += 2
            elif c == 38 and p[i + 1:i + 2] == [2] and i + 4 < len(p):
                r, g, b = p[i + 2:i + 5]
                yield 16 + 36 * round(r / 255 * 5) + 6 * round(g / 255 * 5) + round(b / 255 * 5)
                i += 4
            i += 1


def pick_accent(raw):
    """Первый заметный цвет лого (чёрный пропускаем: на тёмном фоне не видно) или None."""
    for c in sgr_colors(raw):
        if c not in (0, 16):
            return c
    return None


def parse_logo_list(text):
    """Имена лого из вывода fastfetch: по одному в строке, либо `12) "Имя" "Алиас"`."""
    names = {}
    for line in text.splitlines():
        quoted = re.findall(r'"([^"]+)"', line)
        name = quoted[0] if quoted else line.strip()
        if name and not name.endswith(":"):
            names[name] = None
    return list(names)


_LOGOS = None


def fastfetch_logos():
    """Все встроенные лого fastfetch (кэшируется). Пусто, если fastfetch не установлен."""
    global _LOGOS
    if _LOGOS is None:
        _LOGOS = []
        if shutil.which("fastfetch"):
            for cmd in (["fastfetch", "--list-logos", "autocompletion"],
                        ["fastfetch", "--list-logos"]):
                _LOGOS = parse_logo_list(run(cmd, timeout=4))
                if _LOGOS:
                    break
    return _LOGOS


def load_logo(spec, detected, forced=False):
    """spec: auto | имя лого fastfetch | none | путь к файлу.
    -> (lines, accent): accent - номер цвета xterm (0..255) или None."""
    if spec == "none":
        return [], None
    if is_path(spec):
        lines = read_logo_file(os.path.expanduser(spec))
        return (lines or fallback_logo(detected)), DISTROS.get(detected)
    auto = spec == "auto"
    name = detected if auto else spec
    key = name.lower()
    dirs = [os.path.join(config_dir(), "logos")] + SYSTEM_LOGO_DIRS
    for d in dirs:
        lines = read_logo_file(os.path.join(d, f"{key}.txt"))
        if lines:
            return lines, DISTROS.get(key)
    attempts = []
    if shutil.which("fastfetch"):
        # auto: fastfetch сам выберет лого твоего дистра (EndeavourOS, Mint, ...);
        # имя передаём, только если его задали явно (--logo ИМЯ, --distro ИМЯ или клавиша l)
        sel = [] if auto and not forced else ["--logo", name]
        attempts += [
            ["fastfetch", *sel, "--structure", "Break", "--pipe", "false"],
            ["fastfetch", *sel, "-s", "none", "--pipe", "false"],
        ]
    if shutil.which("neofetch"):
        attempts += [["neofetch", "--ascii_distro", key, "-L"]]
    for cmd in attempts:
        raw = run(cmd, timeout=4)
        lines = clean_logo(raw)
        if len(lines) >= 4:
            color = pick_accent(raw)
            return lines, (color if color is not None else DISTROS.get(key))
    return fallback_logo(name), DISTROS.get(key)


def fallback_logo(distro):
    title = distro.upper()
    w = max(len(title) + 6, 18)
    top = "╭" + "─" * (w - 2) + "╮"
    bot = "╰" + "─" * (w - 2) + "╯"
    empty = "│" + " " * (w - 2) + "│"
    mid = "│" + title.center(w - 2) + "│"
    return [top, empty, empty, mid, empty, empty, bot, "", t("hint1").center(w), t("hint2").center(w)]


# ───────────────────────── сбор статистики ─────────────────────────
def read(path):
    try:
        with open(path) as f:
            return f.read()
    except OSError:
        return ""


def cpu_times():
    res = []
    for line in read("/proc/stat").splitlines():
        if line.startswith("cpu"):
            p = line.split()
            vals = list(map(int, p[1:9]))
            idle = vals[3] + vals[4]
            res.append((sum(vals), idle))
    return res  # [0] = общий, дальше ядра


def cpu_temp():
    for h in glob.glob("/sys/class/hwmon/hwmon*"):
        if read(h + "/name").strip() in ("coretemp", "k10temp", "zenpower", "cpu_thermal"):
            t = read(h + "/temp1_input").strip()
            if t.isdigit():
                return int(t) / 1000
    return None


def cpu_model():
    for line in read("/proc/cpuinfo").splitlines():
        if line.startswith("model name"):
            return re.sub(r"\s+", " ", line.split(":", 1)[1]).strip()
    return "CPU"


def mem_info():
    m = {}
    for line in read("/proc/meminfo").splitlines():
        k, v = line.split(":", 1)
        m[k] = int(v.split()[0]) * 1024
    total = m.get("MemTotal", 1)
    used = total - m.get("MemAvailable", 0)
    stotal = m.get("SwapTotal", 0)
    sused = stotal - m.get("SwapFree", 0)
    return used, total, sused, stotal


def net_bytes():
    rx = tx = 0
    for line in read("/proc/net/dev").splitlines()[2:]:
        name, data = line.split(":", 1)
        name = name.strip()
        if name == "lo" or name.startswith(("docker", "veth", "br-", "virbr")):
            continue
        p = data.split()
        rx += int(p[0])
        tx += int(p[8])
    return rx, tx


def gpu_name():
    for line in run(["lspci", "-mm"]).splitlines():
        if "VGA compatible" in line or "3D controller" in line or "Display controller" in line:
            try:
                p = shlex.split(line)
                return f"{p[2]} {p[3]}".replace("Corporation", "").replace("Advanced Micro Devices, Inc. [AMD/ATI]", "AMD").strip()
            except (ValueError, IndexError):
                pass
    return "GPU"


def gpu_stats():
    """-> dict(name?, util, vram_used, vram_total, temp) значения None если нет данных"""
    out = run(["nvidia-smi", "--query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu",
               "--format=csv,noheader,nounits"])
    if out.strip():
        try:
            n, u, mu, mt, t = [x.strip() for x in out.splitlines()[0].split(",")]
            return dict(name=n, util=float(u), vu=float(mu) * 2**20, vt=float(mt) * 2**20, temp=float(t))
        except ValueError:
            pass
    for card in sorted(glob.glob("/sys/class/drm/card[0-9]/device")):
        busy = read(card + "/gpu_busy_percent").strip()
        if busy.isdigit():
            vu = read(card + "/mem_info_vram_used").strip()
            vt = read(card + "/mem_info_vram_total").strip()
            temp = None
            for h in glob.glob(card + "/hwmon/hwmon*/temp1_input"):
                t = read(h).strip()
                if t.isdigit():
                    temp = int(t) / 1000
            return dict(name=None, util=float(busy),
                        vu=float(vu) if vu.isdigit() else None,
                        vt=float(vt) if vt.isdigit() else None, temp=temp)
    return dict(name=None, util=None, vu=None, vt=None, temp=None)


class Stats:
    def __init__(self):
        self.cpu_prev = cpu_times()
        self.net_prev = net_bytes()
        self.t_prev = time.time()
        self.cpu_total = 0.0
        self.cores = []
        self.cpu_hist = deque(maxlen=HIST)
        self.ram_hist = deque(maxlen=HIST)
        self.gpu_hist = deque(maxlen=HIST)
        self.rx_hist = deque(maxlen=HIST)
        self.tx_hist = deque(maxlen=HIST)
        self.rx = self.tx = 0.0
        self.gpu = {}
        self.gname = gpu_name()
        self.cname = cpu_model()
        self.temp = None
        self.mem = (0, 1, 0, 0)

    def update(self):
        now = time.time()
        dt = max(now - self.t_prev, 0.001)
        cur = cpu_times()
        pcts = []
        for (t1, i1), (t0, i0) in zip(cur, self.cpu_prev):
            dtot = t1 - t0
            pcts.append(0.0 if dtot <= 0 else 100.0 * (1 - (i1 - i0) / dtot))
        if pcts:
            self.cpu_total, self.cores = pcts[0], pcts[1:]
        self.cpu_prev = cur
        self.temp = cpu_temp()
        self.mem = mem_info()
        rx, tx = net_bytes()
        self.rx = max(rx - self.net_prev[0], 0) / dt
        self.tx = max(tx - self.net_prev[1], 0) / dt
        self.net_prev = (rx, tx)
        self.t_prev = now
        self.gpu = gpu_stats()
        self.cpu_hist.append(self.cpu_total)
        self.ram_hist.append(100.0 * self.mem[0] / self.mem[1])
        self.gpu_hist.append(self.gpu.get("util") or 0)
        self.rx_hist.append(self.rx)
        self.tx_hist.append(self.tx)


# ───────────────────────── форматирование ─────────────────────────
def hbytes(n):
    for u in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or u == "TB":
            return f"{n:.0f} {u}" if u == "B" else f"{n:.1f} {u}"
        n /= 1024


def hspeed(n):
    return hbytes(n) + "/s"


def spark(vals, width, vmax=None):
    vals = list(vals)[-width:]
    vmax = vmax or max(max(vals, default=0), 1e-9)
    s = "".join(SPARK[min(int(v / vmax * (len(SPARK) - 1) + 0.5), len(SPARK) - 1)] for v in vals)
    return s.rjust(width)


def uptime():
    try:
        s = int(float(read("/proc/uptime").split()[0]))
    except (IndexError, ValueError):
        return "?"
    d, s = divmod(s, 86400)
    h, s = divmod(s, 3600)
    m = s // 60
    return (f"{d}{t('u_d')} " if d else "") + f"{h}{t('u_h')} {m}{t('u_m')}"


# ───────────────────────── отрисовка ─────────────────────────
class UI:
    def __init__(self, scr, detected, pretty, spec, forced=False):
        self.scr = scr
        self.detected = detected
        self.forced = forced  # дистр задан вручную (--distro): auto-лого берём по нему
        self.pretty = pretty
        self.cache = {}
        try:
            curses.curs_set(0)
        except curses.error:
            pass
        curses.use_default_colors()
        self.set_logo(spec)
        curses.init_pair(2, curses.COLOR_GREEN, -1)
        curses.init_pair(3, curses.COLOR_YELLOW, -1)
        curses.init_pair(4, curses.COLOR_RED, -1)
        curses.init_pair(5, curses.COLOR_WHITE, -1)
        self.DIM = curses.A_DIM

    def set_logo(self, spec):
        self.spec = spec
        if spec not in self.cache:
            self.cache[spec] = load_logo(spec, self.detected, self.forced)
        self.logo, accent = self.cache[spec]
        if accent is None:
            accent = DEFAULT_COLOR
        if accent >= curses.COLORS:               # терминал победнее (8/16 цветов)
            accent %= 8
        curses.init_pair(1, accent, -1)           # акцент лого
        self.ACC = curses.color_pair(1)

    def put(self, y, x, s, attr=0):
        h, w = self.scr.getmaxyx()
        if y < 0 or y >= h - 0 or x >= w - 1:
            return
        try:
            self.scr.addstr(y, x, s[: w - x - 1], attr)
        except curses.error:
            pass

    def level(self, pct):
        return curses.color_pair(2 if pct < 50 else 3 if pct < 80 else 4)

    def bar(self, y, x, width, pct, text=""):
        pct = max(0.0, min(100.0, pct))
        filled = int(width * pct / 100)
        self.put(y, x, "[", self.DIM)
        self.put(y, x + 1, "█" * filled, self.level(pct))
        self.put(y, x + 1 + filled, "░" * (width - filled), self.DIM)
        self.put(y, x + width + 1, "]", self.DIM)
        self.put(y, x + width + 3, text, curses.A_BOLD)

    def header(self, y, x, width, title, extra=""):
        self.put(y, x, title, self.ACC | curses.A_BOLD)
        if extra:
            self.put(y, x + len(title) + 2, extra[: max(0, width - len(title) - 2)], self.DIM)

    def draw(self, st, status=""):
        self.scr.erase()
        h, w = self.scr.getmaxyx()
        if h < 18 or w < 50:
            self.put(0, 0, t("small_term"))
            self.scr.refresh()
            return

        logo_w = max((len(l) for l in self.logo), default=0)
        show_logo = bool(self.logo) and w >= logo_w + 2 + 52
        x0 = (logo_w + 4) if show_logo else 1
        pw = w - x0 - 2  # ширина правой панели

        # ── левая панель: лого + инфо
        if show_logo:
            y = 1
            for line in self.logo[: h - 8]:
                self.put(y, 1, line, self.ACC | curses.A_BOLD)
                y += 1
            y += 1
            info = [(t("lbl_os"), self.pretty), (t("lbl_kernel"), os.uname().release),
                    (t("lbl_host"), os.uname().nodename), (t("lbl_uptime"), uptime())]
            for k, v in info:
                if y >= h - 1:
                    break
                self.put(y, 1, f"{k}: ", self.ACC | curses.A_BOLD)
                self.put(y, 1 + len(k) + 2, v[: max(0, logo_w - len(k) - 2)])
                y += 1
            self.scr.vline(1, x0 - 2, curses.ACS_VLINE, h - 2)

        # ── правая панель
        y = 1
        bw = max(10, min(40, pw - 22))
        sw = max(10, pw)

        # CPU
        self.header(y, x0, pw, "CPU", st.cname)
        y += 1
        t = f"  {st.temp:.0f}°C" if st.temp is not None else ""
        self.bar(y, x0, bw, st.cpu_total, f"{st.cpu_total:5.1f}%{t}")
        y += 1
        self.put(y, x0, t("cores").ljust(6), self.DIM)
        for i, c in enumerate(st.cores[: max(0, pw - 8)]):
            ch = SPARK[min(int(c / 100 * 7 + 0.5), 7)]
            self.put(y, x0 + 6 + i, ch, self.level(c))
        y += 1
        self.put(y, x0, spark(st.cpu_hist, sw), self.ACC)
        y += 2

        # RAM
        used, total, su, stt = st.mem
        self.header(y, x0, pw, "RAM", f"{hbytes(used)} / {hbytes(total)}")
        y += 1
        self.bar(y, x0, bw, 100.0 * used / total, f"{100.0 * used / total:5.1f}%")
        y += 1
        if stt:
            self.put(y, x0, f"swap  {hbytes(su)} / {hbytes(stt)}", self.DIM)
            y += 1
        self.put(y, x0, spark(st.ram_hist, sw, 100), self.ACC)
        y += 2

        # GPU
        g = st.gpu
        self.header(y, x0, pw, "GPU", g.get("name") or st.gname)
        y += 1
        if g.get("util") is not None:
            tt = f"  {g['temp']:.0f}°C" if g.get("temp") is not None else ""
            self.bar(y, x0, bw, g["util"], f"{g['util']:5.1f}%{tt}")
            y += 1
            if g.get("vu") is not None and g.get("vt"):
                self.put(y, x0, f"VRAM  {hbytes(g['vu'])} / {hbytes(g['vt'])}", self.DIM)
                y += 1
            self.put(y, x0, spark(st.gpu_hist, sw, 100), self.ACC)
            y += 1
        else:
            self.put(y, x0, t("no_gpu"), self.DIM)
            y += 1
        y += 1

        # NET
        self.header(y, x0, pw, "NET")
        y += 1
        vmax = max(max(st.rx_hist, default=0), max(st.tx_hist, default=0), 1024)
        self.put(y, x0, "↓ ", curses.color_pair(2) | curses.A_BOLD)
        self.put(y, x0 + 2, f"{hspeed(st.rx):<12}", curses.A_BOLD)
        self.put(y, x0 + 15, spark(st.rx_hist, max(0, sw - 15), vmax), curses.color_pair(2))
        y += 1
        self.put(y, x0, "↑ ", curses.color_pair(3) | curses.A_BOLD)
        self.put(y, x0 + 2, f"{hspeed(st.tx):<12}", curses.A_BOLD)
        self.put(y, x0 + 15, spark(st.tx_hist, max(0, sw - 15), vmax), curses.color_pair(3))

        self.put(h - 1, 1, status, self.DIM)
        self.scr.refresh()


def fmt_refresh(r):
    return f"{r:g}{t('sec')}"


def step_refresh(cur, direction):
    """direction=+1 -> быстрее (меньше интервал), -1 -> медленнее."""
    steps = sorted(set(REFRESH_STEPS + [cur]))
    i = steps.index(cur)
    i = max(0, min(len(steps) - 1, i - direction))
    return steps[i]


def next_logo(spec, step=1):
    """Листает по кругу: auto -> none -> все лого fastfetch -> auto. step=-1 - назад."""
    choices = ["auto", "none"] + fastfetch_logos()
    low = [c.lower() for c in choices]
    if spec.lower() not in low:
        return choices[0]  # кастомный путь -> возвращаемся к auto
    return choices[(low.index(spec.lower()) + step) % len(choices)]


def run_ui(scr, detected, pretty, cfg, cfg_path, forced=False):
    ui = UI(scr, detected, pretty, cfg["logo"], forced)
    st = Stats()
    flash, flash_until = "", 0.0
    time.sleep(0.3)
    next_t = 0.0
    while True:
        now = time.time()
        if now >= next_t:
            st.update()
            next_t = now + cfg["refresh"]
        status = (f"{t('help')}  |  {t('st_refresh')}: {fmt_refresh(cfg['refresh'])}"
                  f"  {t('st_logo')}: {cfg['logo']}  {t('st_lang')}: {resolve_lang(cfg['lang'])}")
        if now < flash_until:
            status = flash
        ui.draw(st, status)
        scr.timeout(max(50, int((next_t - time.time()) * 1000)))
        k = scr.getch()
        if k in (ord("q"), ord("Q"), 27):
            break
        elif k in (ord("+"), ord("="), curses.KEY_UP):
            cfg["refresh"] = step_refresh(cfg["refresh"], +1)
            next_t = time.time() + cfg["refresh"]
        elif k in (ord("-"), ord("_"), curses.KEY_DOWN):
            cfg["refresh"] = step_refresh(cfg["refresh"], -1)
            next_t = time.time() + cfg["refresh"]
        elif k in (ord("l"), ord("L")):
            cfg["logo"] = next_logo(cfg["logo"], 1 if k == ord("l") else -1)
            ui.set_logo(cfg["logo"])
        elif k in (ord("g"), ord("G")):
            cfg["lang"] = "en" if resolve_lang(cfg["lang"]) == "ru" else "ru"
            set_lang(cfg["lang"])
            ui.cache.clear()  # заглушка лого содержит текст на текущем языке
            ui.set_logo(cfg["logo"])
        elif k in (ord("s"), ord("S")):
            ok = save_config(cfg_path, cfg)
            flash = t("saved", path=cfg_path) if ok else t("save_fail")
            flash_until = time.time() + 3


def parse_args(argv=None):
    # сначала вытаскиваем --lang, чтобы --help уже был на нужном языке
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("--lang")
    known, _ = pre.parse_known_args(argv)
    set_lang(resolve_lang(known.lang))
    p = argparse.ArgumentParser(prog=APP, description=t("a_desc"))
    p.add_argument("--logo", help=t("a_logo"))
    p.add_argument("--list-logos", action="store_true", help=t("a_list"))
    p.add_argument("--refresh", type=float, help=t("a_refresh", lo=REFRESH_MIN, hi=REFRESH_MAX))
    p.add_argument("--lang", choices=["auto", *LANGS], help=t("a_lang"))
    p.add_argument("--config", help=t("a_config"))
    p.add_argument("--distro", help=t("a_distro"))
    p.add_argument("--version", action="version", version=f"{APP} {__version__}")
    return p.parse_args(argv)


def cli(argv=None):
    """Точка входа (для AUR / console_scripts: gostfetch = gostfetch:cli)."""
    args = parse_args(argv)
    if args.list_logos:
        names = fastfetch_logos()
        if not names:
            print(f"{APP}: {t('no_fastfetch')}", file=sys.stderr)
            return 1
        print("\n".join(names))
        return 0
    cfg_path = os.path.expanduser(args.config) if args.config else default_config_path()
    cfg, warn = load_config(cfg_path)
    if warn:
        print(f"{APP}: {warn}", file=sys.stderr)
        time.sleep(1.5)
    if args.logo:
        cfg["logo"] = args.logo
    if args.refresh is not None:
        cfg["refresh"] = clamp_refresh(args.refresh)
    if args.lang:
        cfg["lang"] = args.lang
    set_lang(resolve_lang(cfg["lang"]))
    detected, pretty = detect_distro(args.distro)
    try:
        curses.wrapper(run_ui, detected, pretty, cfg, cfg_path, bool(args.distro))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    sys.exit(cli())
