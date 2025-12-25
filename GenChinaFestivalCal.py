
# -*- coding: utf-8 -*-
"""
生成包含中国传统节日的 iCalendar (.ics) 文件，不含假期
- 区间：从当前日期前一年年初到下一年年底”
- 文件名：ChinaFestivalCal.ics

依赖安装（推荐 uv）：
  uv venv --python python3
  source .venv/bin/activate
  uv pip install zhdate
"""

from __future__ import annotations
from datetime import datetime, date, timedelta, timezone
from typing import List, Tuple, Dict
import math

# ---- 依赖 ----
try:
    from zhdate import ZhDate  # 农历 <-> 公历
except Exception as e:
    raise RuntimeError("缺少 zhdate，请先安装：uv pip install zhdate") from e


# ---- 基本配置 ----
OUTPUT_FILE = "ChinaFestivalCal.ics"
CALENDAR_NAME = "中国传统节日"
CALENDAR_DESCRIPTION = (
    "中国传统节日，不含假期。"
)
EVENT_TRANSP = "TRANSPARENT"  # 不占用日程


# ---- 工具函数 ----
def today_local_date() -> date:
    return datetime.now().date()


def dtstamp_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def yyyymmdd(d: date) -> str:
    return d.strftime("%Y%m%d")


def format_date_ics(d: date) -> str:
    return d.strftime("%Y%m%d")


def nth_weekday_of_month(year: int, month: int, weekday: int, n: int) -> date:
    """
    计算某年某月的第 n 个 weekday（Monday=0 ... Sunday=6）
    例：母亲节=5月第2个星期日 -> weekday=6, n=2
    """
    first = date(year, month, 1)
    shift = (weekday - first.weekday() + 7) % 7
    day = 1 + shift + (n - 1) * 7
    return date(year, month, day)


def lunar_to_solar(lunar_year: int, lunar_month: int, lunar_day: int) -> date:
    """农历转公历（返回 date）"""
    return ZhDate(lunar_year, lunar_month, lunar_day).to_datetime().date()


def last_day_of_layue(lunar_year: int) -> int:
    """返回当年腊月最后一天（29 或 30），用于除夕"""
    try:
        ZhDate(lunar_year, 12, 30).to_datetime()
        return 30
    except Exception:
        return 29


# ---- 仅用“日期级”节气公式（21 世纪，2001-2100）----
def _century21_solar_term_day(year: int, C: float) -> int:
    """
    “寿星公式”的日计算：
      D = floor(Y * 0.2422 + C) - floor(Y / 4)
    其中 Y = year % 100，C 为该节气在 21 世纪的常数。
    返回公历“日”（int）。
    仅在 2001-2100 年建议使用；超出范围请改用更严谨天文算法或分世纪常数。
    """
    Y = year % 100
    return int(math.floor(Y * 0.2422 + C) - math.floor(Y / 4))


def get_qingming_date(year: int) -> date | None:
    """
    清明（4 月）：C=4.81。常见结果为 4/4 或 4/5。
    适用范围：2001-2100；超出范围返回 None。
    """
    if not (2001 <= year <= 2100):
        return None
    day = _century21_solar_term_day(year, 4.81)
    return date(year, 4, day)


def get_solstice_dates(year: int) -> Dict[str, date]:
    """
    夏至（6 月，C=21.37）与 冬至（12 月，C=21.94），仅日期级精度。
    已包含一个已知修正：2021 年冬至 -1 天。
    适用范围：2001-2100；超出范围返回空映射。
    """
    result: Dict[str, date] = {}
    if not (2001 <= year <= 2100):
        return result

    # 夏至：通常 6/20 ~ 6/22（多为 6/21）
    day_summer = _century21_solar_term_day(year, 21.37)
    result["夏至"] = date(year, 6, day_summer)

    # 冬至：通常 12/21 ~ 12/22
    day_winter = _century21_solar_term_day(year, 21.94)
    if year == 2021:
        day_winter -= 1  # 已知修正样例
    result["冬至"] = date(year, 12, day_winter)

    return result


# ---- 节日构造 ----
def build_lunar_festivals_for_lunar_year(lunar_year: int) -> List[Tuple[str, date, str]]:
    """
    农历节日列表：[(name, date, category)]
    category = "Lunar"
    包含：除夕、春节、元宵、上巳节/龙抬头、端午、七夕、中元、中秋、重阳、下元、腊八、小年（腊月二十三）
    """
    names_fixed = [
        ("春节", 1, 1),
        ("元宵节", 1, 15),
        ("上巳节/龙抬头", 3, 3),
        ("端午节", 5, 5),
        ("七夕节", 7, 7),
        ("中元节", 7, 15),
        ("中秋节", 8, 15),
        ("重阳节", 9, 9),
        ("下元节", 10, 15),
        ("腊八节", 12, 8),
        ("小年", 12, 23),  # 仅腊月二十三
    ]
    items: List[Tuple[str, date, str]] = []
    for name, m, d in names_fixed:
        try:
            items.append((name, lunar_to_solar(lunar_year, m, d), "Lunar"))
        except Exception:
            # 罕见特殊年若失败则跳过该项
            pass

    # 除夕（腊月最后一天）
    try:
        last_d = last_day_of_layue(lunar_year)
        items.append(("除夕", lunar_to_solar(lunar_year, 12, last_d), "Lunar"))
    except Exception:
        pass

    return items


def build_jieqi_based_festivals(year: int) -> List[Tuple[str, date, str]]:
    """
    清明、夏至、冬至（不含寒食）
    category = "Solar Term"
    """
    items: List[Tuple[str, date, str]] = []

    qingming = get_qingming_date(year)
    if qingming:
        items.append(("清明节", qingming, "Solar Term"))

    solstices = get_solstice_dates(year)
    if "夏至" in solstices:
        items.append(("夏至", solstices["夏至"], "Solar Term"))
    if "冬至" in solstices:
        items.append(("冬至", solstices["冬至"], "Solar Term"))

    return items


def build_gregorian_festivals(year: int) -> List[Tuple[str, date, str]]:
    """
    公历纪念日（不含记者节）
    category = "Gregorian"
    """
    fixed = [
        ("元旦", date(year, 1, 1)),
        ("情人节", date(year, 2, 14)),
        ("植树节", date(year, 3, 12)),
        ("劳动节", date(year, 5, 1)),
        ("青年节", date(year, 5, 4)),
        ("儿童节", date(year, 6, 1)),
        ("教师节", date(year, 9, 10)),
    ]
    items = [(name, d, "Gregorian") for name, d in fixed]

    # 母亲节：5 月第 2 个星期日
    mothers = nth_weekday_of_month(year, 5, weekday=6, n=2)
    items.append(("母亲节", mothers, "Gregorian"))

    # 父亲节：6 月第 3 个星期日
    fathers = nth_weekday_of_month(year, 6, weekday=6, n=3)
    items.append(("父亲节", fathers, "Gregorian"))

    return items


def collect_all_events(start_date: date, end_date: date) -> List[Tuple[str, date, str]]:
    """
    汇总所有节日并过滤在 [start_date, end_date] 区间内
    返回 [(name, date, category)]
    """
    events: List[Tuple[str, date, str]] = []

    # 覆盖腊月跨年：农历年份取较宽范围
    lunar_year_start = start_date.year - 1
    lunar_year_end = end_date.year + 1

    for ly in range(lunar_year_start, lunar_year_end + 1):
        for name, d, cat in build_lunar_festivals_for_lunar_year(ly):
            if start_date <= d <= end_date:
                events.append((name, d, cat))

    # 节气：按公历年取（多取一年以防边界）
    for gy in range(start_date.year - 1, end_date.year + 2):
        for name, d, cat in build_jieqi_based_festivals(gy):
            if start_date <= d <= end_date:
                events.append((name, d, cat))

    # 公历纪念日
    for gy in range(start_date.year, end_date.year + 1):
        for name, d, cat in build_gregorian_festivals(gy):
            if start_date <= d <= end_date:
                events.append((name, d, cat))

    # 去重：(name, date) 维度，保留唯一
    uniq: Dict[Tuple[str, date], Tuple[str, date, str]] = {}
    for name, d, cat in events:
        key = (name, d)
        if key not in uniq:
            uniq[key] = (name, d, cat)

    events = list(uniq.values())

    # 稳定排序：日期 + 名称（保证 UID 递增顺序稳定）
    events.sort(key=lambda x: (x[1], x[0]))
    return events


def build_ics(events: List[Tuple[str, date, str]]) -> str:
    """
    生成 ICS 文本，按同日事件计数生成 UID：YYYYMMDDx
    """
    lines: List[str] = []
    lines.append("BEGIN:VCALENDAR")
    lines.append("VERSION:2.0")
    lines.append("PRODID:-//China Festivals Generator//CN")
    lines.append("CALSCALE:GREGORIAN")
    lines.append("METHOD:PUBLISH")
    lines.append(f"X-WR-CALNAME:{CALENDAR_NAME}")
    lines.append(f"X-WR-CALDESC:{CALENDAR_DESCRIPTION}")

    stamp = dtstamp_utc()
    per_date_counter: Dict[str, int] = {}

    for name, d, cat in events:
        ds = yyyymmdd(d)
        x = per_date_counter.get(ds, 0)
        uid = f"{ds}{x}"
        per_date_counter[ds] = x + 1

        lines.append("BEGIN:VEVENT")
        lines.append(f"UID:{uid}")
        lines.append(f"DTSTAMP:{stamp}")
        lines.append(f"SUMMARY:{name}")
        lines.append(f"DTSTART;VALUE=DATE:{format_date_ics(d)}")
        lines.append(f"CATEGORIES:{cat}")
        lines.append(f"TRANSP:{EVENT_TRANSP}")
        lines.append(f"DESCRIPTION:{name}")
        lines.append("END:VEVENT")

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines)


def main():
    # 时间范围：当前日期的前一年 1/1 至 下一年 12/31
    today = today_local_date()
    start_date = date(today.year - 1, 1, 1)
    end_date = date(today.year + 1, 12, 31)

    events = collect_all_events(start_date, end_date)
    ics_text = build_ics(events)

    with open(OUTPUT_FILE, "w", encoding="utf-8", newline="\n") as f:
        f.write(ics_text)

    print(f"已生成：{OUTPUT_FILE}")
    print(f"覆盖范围：{start_date} ~ {end_date}")
    print(f"事件总数：{len(events)}")


if __name__ == "__main__":
    main()
