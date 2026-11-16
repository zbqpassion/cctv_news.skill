#!/usr/bin/env python3
"""Count CCTV News stories per topic, with aliases and window trend labels.

Usage:
  trend-analysis.py [DAYS] [--until YYYYMMDD] [--summary] '主题=同义词1|同义词2' ...

The window is the last DAYS archive files dated on or before --until
(default: the newest archive). Trend labels compare daily averages, so the
tables print averages rather than raw totals of unequal windows.
"""
import glob
import os
import re
import sys

DEFAULT_SPECS = [
    '人工智能=人工智能|AI|大模型',
    '十五五=十五五',
    '扩大内需=扩大内需|提振消费',
    '高端制造=高端制造|先进制造|智能制造',
]


def parse_spec(spec: str) -> tuple[str, list[str]]:
    if '=' in spec:
        label, raw_aliases = spec.split('=', 1)
    else:
        label, raw_aliases = spec, spec
    aliases = [item.strip() for item in raw_aliases.split('|') if item.strip()]
    return label.strip(), aliases or [label.strip()]


def extract_stories(content: str) -> list[str]:
    marker = '## 详细新闻'
    if marker not in content:
        return []
    detailed = content.split(marker, 1)[1]
    return [part.strip() for part in re.split(r'(?m)^###\s+', detailed) if part.strip()]


def story_count(stories: list[str], aliases: list[str]) -> int:
    return sum(1 for story in stories if any(alias in story for alias in aliases))


def classify_trend(counts: list[int], recent_days: int) -> tuple[float, float, str]:
    """Return (recent daily average, earlier daily average, status)."""
    if not counts:
        return 0.0, 0.0, '持平'
    window = min(recent_days, len(counts))
    recent = counts[-window:]
    earlier = counts[:-window]
    recent_rate = sum(recent) / len(recent)
    earlier_rate = sum(earlier) / len(earlier) if earlier else 0.0
    if earlier_rate == 0:
        status = '升温' if recent_rate > 0 else '持平'
    elif recent_rate >= earlier_rate * 1.35 and sum(recent) >= 2:
        status = '升温'
    elif recent_rate <= earlier_rate * 0.65:
        status = '降温'
    else:
        status = '持平'
    return recent_rate, earlier_rate, status


def load_window(days: int, until: str | None = None):
    skill_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    news_dir = os.path.join(skill_dir, 'news')
    paths = sorted(glob.glob(os.path.join(news_dir, '[0-9]' * 8 + '.md')))
    if until:
        paths = [path for path in paths if os.path.basename(path)[:8] <= until]
    paths = paths[-days:]
    rows = []
    for path in paths:
        date_str = os.path.basename(path)[:8]
        try:
            with open(path, 'r', encoding='utf-8') as handle:
                stories = extract_stories(handle.read())
        except OSError:
            continue
        rows.append((date_str, stories))
    return rows


def run_analysis(days=10, specs=None, summary=False, until=None):
    parsed = [parse_spec(item) for item in (specs or DEFAULT_SPECS)]
    rows = load_window(days, until)
    if not rows:
        print('未找到任何新闻文件，请先执行抓取。')
        return 1
    if until and rows[-1][0] != until:
        print(f'警告：窗口内没有 {until} 的归档，最新一期是 {rows[-1][0]}。', file=sys.stderr)

    counts_by_label = {
        label: [story_count(stories, aliases) for _, stories in rows]
        for label, aliases in parsed
    }

    if not summary:
        print('| 日期 | ' + ' | '.join(label for label, _ in parsed) + ' |')
        print('| :---: | ' + ' | '.join(':---:' for _ in parsed) + ' |')
        for index, (date_str, _) in enumerate(rows):
            date_label = f'{date_str[4:6]}月{date_str[6:8]}日'
            values = [str(counts_by_label[label][index]) for label, _ in parsed]
            print('| ' + ' | '.join([date_label, *values]) + ' |')
        print()
        print('| 主题 | 近3日日均 | 此前日均 | 趋势 |')
        print('| :--- | :---: | :---: | :---: |')
        for label, _ in parsed:
            recent, earlier, status = classify_trend(counts_by_label[label], 3)
            print(f'| {label} | {recent:.1f} | {earlier:.1f} | {status} |')
        return 0

    print(f'统计窗口：{rows[0][0]} 至 {rows[-1][0]}，共 {len(rows)} 期。')
    print()
    print('| 主题 | 涉及日期 | 相关报道 | 近7日日均 | 此前日均 | 状态 |')
    print('| :--- | :---: | :---: | :---: | :---: | :---: |')
    for label, _ in parsed:
        counts = counts_by_label[label]
        covered_days = sum(1 for count in counts if count > 0)
        recent, earlier, status = classify_trend(counts, 7)
        long_status = {'升温': '强化', '持平': '延续', '降温': '降温'}[status]
        print(f'| {label} | {covered_days} | {sum(counts)} | {recent:.1f} | {earlier:.1f} | {long_status} |')
    return 0


def main(argv: list[str]) -> int:
    args = list(argv)
    until = None
    if '--until' in args:
        index = args.index('--until')
        if index + 1 >= len(args) or not re.fullmatch(r'\d{8}', args[index + 1]):
            print('--until 需要 YYYYMMDD 格式的日期。', file=sys.stderr)
            return 64
        until = args[index + 1]
        del args[index:index + 2]
    summary = '--summary' in args
    args = [arg for arg in args if arg != '--summary']
    days = 10
    if args:
        try:
            days = int(args[0])
            args = args[1:]
        except ValueError:
            pass
    unknown = [arg for arg in args if arg.startswith('--')]
    if unknown:
        print(f'不支持的参数：{" ".join(unknown)}', file=sys.stderr)
        return 64
    return run_analysis(days=days, specs=args or None, summary=summary, until=until)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
