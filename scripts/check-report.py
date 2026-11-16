#!/usr/bin/env python3
"""Archive facts and report validation for the CCTV News daily report.

Usage:
  check-report.py facts YYYYMMDD            # facts the report must match
  check-report.py check YYYYMMDD REPORT.md  # validate a draft or final report

Exit codes for `check`: 0 pass (warnings allowed), 1 rule errors,
2 fatal structure problems (report unusable), 3 archive missing or invalid.

Length counts ("字数") are all non-whitespace characters, excluding links.
"""
import glob
import json
import os
import re
import sys

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NEWS_DIR = os.path.join(SKILL_DIR, 'news')
STATE_FILE = os.path.join(SKILL_DIR, 'state', 'topics.json')
BAD_MARKERS = ('CCTV.com - ERROR', 'ABSTRACT_NOT_FOUND', 'CONTENT_NOT_FOUND', 'TITLE_NOT_FOUND')
URL_RE = re.compile(r'https?://[^\s)\]>"]+')
LINK_RE = re.compile(r'\[[^\]]*\]\([^)]*\)')
SECTIONS = ['今日大事', 'A股当日增量信号', '滚动30日长期主线', '近10日热词', '详细新闻逐条缩写']
NUMERALS = ['一', '二', '三', '四', '五']
SIGNAL_LABELS = ['相关方向', '影响方向', '影响周期', '可信度', '判断依据']
LINK_WINDOW = 45


class ArchiveError(Exception):
    pass


def text_len(text: str) -> int:
    return len(re.sub(r'\s', '', LINK_RE.sub('', text)))


def norm(text: str) -> str:
    return re.sub(r'\s', '', text)


def load_archive(date: str) -> dict:
    path = os.path.join(NEWS_DIR, f'{date}.md')
    try:
        with open(path, 'r', encoding='utf-8') as handle:
            text = handle.read()
    except OSError:
        raise ArchiveError(f'归档不存在：news/{date}.md')
    for marker in BAD_MARKERS:
        if marker in text:
            raise ArchiveError(f'归档含错误标记 {marker}')
    if '## 新闻摘要' not in text or '## 详细新闻' not in text:
        raise ArchiveError('归档缺少“新闻摘要”或“详细新闻”')
    if f'（{date}）' not in text.split('\n', 1)[0]:
        raise ArchiveError('归档首行日期与目标日期不符')
    head, detail = text.split('## 详细新闻', 1)
    program = re.search(r'\[查看原文\]\((https?://[^)]+)\)', head)
    stories = []
    for part in re.split(r'(?m)^###\s+', detail)[1:]:
        title, _, body = part.partition('\n')
        title = title.strip()
        urls = re.findall(r'\[查看原文\]\((https?://[^)]+)\)', body)
        briefs = []
        if '联播快讯' in title:
            briefs = [b.strip() for b in re.findall(r'(?m)^\*\*(.+?)\*\*\s*$', body)
                      if not b.startswith('央视网消息')]
        stories.append({
            'title': title,
            'url': urls[-1] if urls else None,
            'brief': '联播快讯' in title,
            'briefs': briefs,
            'body_len': text_len(body),
        })
    if len(stories) < 3:
        raise ArchiveError(f'详细新闻只有 {len(stories)} 条，疑似抓取不完整')
    return {'date': date, 'program_url': program.group(1) if program else None, 'stories': stories}


def status_line(archive: dict) -> str:
    parts = [f'{s["title"]} {len(s["briefs"])} 条' for s in archive['stories'] if s['brief']]
    extra = f'，其中{"、".join(parts)}' if parts else ''
    return f'> 数据状态：央视网文字稿已就绪（共 {len(archive["stories"])} 条详细新闻{extra}）'


def cmd_facts(date: str) -> int:
    try:
        archive = load_archive(date)
    except ArchiveError as error:
        print(f'归档无效：{error}')
        return 3
    stories = archive['stories']
    print(f'目标日期：{date}')
    print(f'本期央视文字稿链接：{archive["program_url"] or "缺失，不显示"}')
    print(f'详细新闻条数：{len(stories)}（摘要不计入，每个快讯合集计 1 条）')
    print('顶部数据状态行固定写成：')
    print(status_line(archive))
    print('第五部分必须按下列序号、标题、链接逐条列出：')
    for index, story in enumerate(stories, 1):
        kind = f'快讯合集，共 {len(story["briefs"])} 条' if story['brief'] else f'原文约 {story["body_len"]} 字'
        print(f'{index}. {story["title"]}｜{kind}｜{story["url"] or "无链接"}')
        for brief in story['briefs']:
            print(f'   - {brief}')
    return 0


def allowed_urls(date: str) -> set[str]:
    paths = sorted(glob.glob(os.path.join(NEWS_DIR, '[0-9]' * 8 + '.md')))
    paths = [p for p in paths if os.path.basename(p)[:8] <= date][-LINK_WINDOW:]
    urls: set[str] = set()
    for path in paths:
        try:
            with open(path, 'r', encoding='utf-8') as handle:
                urls.update(URL_RE.findall(handle.read()))
        except OSError:
            continue
    return urls


def split_sections(lines: list[str]) -> tuple[list[str], list[tuple[str, list[str]]]]:
    preamble: list[str] = []
    sections: list[tuple[str, list[str]]] = []
    for line in lines[1:]:
        if line.startswith('## '):
            sections.append((line[3:].strip(), []))
        elif sections:
            sections[-1][1].append(line)
        else:
            preamble.append(line)
    return preamble, sections


def split_items(body: list[str]) -> list[tuple[int, str, list[str]]]:
    """Split a section into `**N. 标题**` items."""
    items: list[tuple[int, str, list[str]]] = []
    for line in body:
        match = re.match(r'^\*\*(\d+)\. (.+?)\*\*\s*$', line)
        if match:
            items.append((int(match.group(1)), match.group(2).strip(), []))
        elif items:
            items[-1][2].append(line)
    return items


def load_state(date: str) -> dict:
    try:
        with open(STATE_FILE, 'r', encoding='utf-8') as handle:
            state = json.load(handle)
    except (OSError, ValueError):
        return {}
    return state if state.get('date') == date else {}


def cmd_check(date: str, report_path: str) -> int:
    fatal: list[str] = []
    errors: list[str] = []
    warns: list[str] = []
    try:
        archive = load_archive(date)
    except ArchiveError as error:
        print(f'归档无效：{error}')
        return 3
    try:
        with open(report_path, 'r', encoding='utf-8') as handle:
            raw = handle.read()
    except OSError as error:
        print(f'无法读取报告：{error}')
        return 2
    lines = raw.replace('\r\n', '\n').strip('\n').split('\n')
    stories = archive['stories']

    # --- overall structure
    pretty = f'{date[:4]}年{date[4:6]}月{date[6:8]}日'
    first = f'# 《新闻联播》每日研判（{pretty}）'
    if lines[0].rstrip() != first:
        fatal.append(f'第一行必须是：{first}')
    preamble, sections = split_sections(lines)
    names = [name for name, _ in sections]
    expected = [f'{NUMERALS[i]}、{SECTIONS[i]}' for i in range(5)]
    if len(names) != 5 or any(not norm(names[i]).startswith(norm(expected[i])) for i in range(min(5, len(names)))):
        fatal.append(f'二级标题必须正好是这五个且顺序固定：{"；".join(expected)}。当前：{"；".join(names) or "无"}')
    for number, line in enumerate(lines[1:], 2):
        if re.match(r'^#{3,}\s', line):
            errors.append(f'第 {number} 行使用了三级或更深标题：{line[:40]}')
        elif re.match(r'^#\s', line):
            errors.append(f'第 {number} 行出现第二个一级标题')
        if re.match(r'^\d+\.\s+\*\*', line):
            errors.append(f'第 {number} 行用了自动有序列表做标题，应写成 **N. 标题**：{line[:40]}')
        stripped = URL_RE.sub('', line).replace('**', '')
        if re.search(r'(?<![\w*])\*[^\s*][^*]*\*(?![\w*])', stripped):
            errors.append(f'第 {number} 行疑似斜体：{line[:40]}')
    if len(fatal) or len(sections) != 5:
        return report(fatal, errors, warns)

    # --- top block
    top = '\n'.join(preamble)
    count = re.search(r'共\s*(\d+)\s*条', top)
    if not count or int(count.group(1)) != len(stories):
        errors.append(f'顶部数据状态的条数应为 {len(stories)}，固定写成：{status_line(archive)}')
    if archive['program_url'] and f'[查看本期央视文字稿]({archive["program_url"]})' not in top:
        errors.append(f'顶部缺少 [查看本期央视文字稿]({archive["program_url"]})')
    if not all(line.startswith('>') for line in preamble if line.strip() and line.strip() != '---'):
        warns.append('顶部数据状态和文字稿链接应放在同一个引用块里')

    # --- links
    known = allowed_urls(date)
    for url in sorted(set(URL_RE.findall(raw))):
        if url not in known:
            errors.append(f'链接不在归档中，疑似虚构或抄错：{url}')

    body = {SECTIONS[i]: sections[i][1] for i in range(5)}

    # --- 一、今日大事
    events = split_items(body['今日大事'])
    if not 3 <= len(events) <= 5:
        errors.append(f'今日大事应为 3 至 5 条，当前 {len(events)} 条')
    for number, title, content in events:
        if not URL_RE.search('\n'.join(content)):
            warns.append(f'今日大事第 {number} 条缺少央视原文链接')
        if text_len('\n'.join(content)) > 160:
            warns.append(f'今日大事第 {number} 条 {text_len(chr(10).join(content))} 字，应控制在 1 至 2 句（约 120 字内）')

    # --- 二、A股当日增量信号
    signals = split_items(body['A股当日增量信号'])
    if len(signals) > 4:
        errors.append(f'A股增量信号最多 4 条，当前 {len(signals)} 条')
    if not signals and '当日无明显增量信号' not in '\n'.join(body['A股当日增量信号']):
        errors.append('没有信号时须写“当日无明显增量信号”')
    high = 0
    for number, title, content in signals:
        text = '\n'.join(content)
        fields = dict(re.findall(r'(?m)^- \*\*(.+?)[：:]\*\*\s*(.*)$', text))
        for label in SIGNAL_LABELS:
            if label not in fields:
                errors.append(f'信号第 {number} 条缺少字段“{label}”，格式为 - **{label}：** 值')
        if fields.get('可信度', '').strip().startswith('高'):
            high += 1
        direction = fields.get('影响方向', '').strip()
        if direction and direction not in ('偏正面', '偏负面', '影响分化', '中性'):
            warns.append(f'信号第 {number} 条影响方向“{direction}”不在四个固定取值内')
        basis = text_len(fields.get('判断依据', ''))
        if basis > 170:
            warns.append(f'信号第 {number} 条判断依据 {basis} 字，应不超过 150 字')
        if not URL_RE.search(text):
            warns.append(f'信号第 {number} 条缺少央视原文链接')
    if high > 1:
        errors.append(f'可信度“高”最多 1 条，当前 {high} 条；没有预算、招标、订单或经营数据的降为“中”或“低”')

    # --- 三、四：与登记保持一致
    state = load_state(date)
    mainlines = split_items(body['滚动30日长期主线'])
    if not 2 <= len(mainlines) <= 4:
        errors.append(f'长期主线应为 2 至 4 条，当前 {len(mainlines)} 条')
    table = [line for line in body['近10日热词'] if line.startswith('|')]
    hot_labels = [cell.strip() for cell in table[0].strip('|').split('|')][1:] if table else []
    if len(hot_labels) != 4:
        errors.append(f'热词表应正好 4 个主题，当前 {len(hot_labels)} 个')
    date_rows = [line for line in table if re.match(r'^\|\s*\d{2}月\d{2}日', line)]
    target_row = f'{date[4:6]}月{date[6:8]}日'
    if not date_rows or target_row not in date_rows[-1]:
        errors.append(f'热词表最后一行应是目标日期 {target_row}，请用 --until {date} 重新统计')
    if not state:
        errors.append(f'本期主线和热词尚未登记：先运行 python3 scripts/topics.py set --date {date} ...')
    else:
        titles = [title for _, title, _ in mainlines]
        if [norm(t) for t in titles] != [norm(t) for t in state.get('mainlines', [])]:
            errors.append('长期主线标题与登记不一致。登记：' + '；'.join(state.get('mainlines', [])))
        registered = [spec.split('=', 1)[0].strip() for spec in state.get('hotwords', [])]
        if sorted(hot_labels) != sorted(registered):
            errors.append('热词主题与登记不一致。登记：' + '；'.join(registered))

    # --- 五、详细新闻逐条缩写
    detail = body['详细新闻逐条缩写']
    entries: list[dict] = []
    for line in detail:
        normal = re.match(r'^\*\*(\d+)\. (.+?)\*\*\s*$', line)
        summary = re.match(r'^<summary>\s*(\d+)\. (.+?)（共\s*(\d+)\s*条', line)
        if normal:
            entries.append({'num': int(normal.group(1)), 'title': normal.group(2).strip(), 'brief': False, 'lines': []})
        elif summary:
            entries.append({'num': int(summary.group(1)), 'title': summary.group(2).strip(), 'brief': True,
                            'count': int(summary.group(3)), 'lines': []})
        elif entries:
            entries[-1]['lines'].append(line)
    detail_text = '\n'.join(detail)
    if re.search(r'<details[^>]*\bopen\b', detail_text):
        errors.append('<details> 不得带 open 属性')
    if detail_text.count('<details') != detail_text.count('</details>'):
        errors.append('<details> 与 </details> 数量不一致')
    if len(entries) != len(stories):
        fatal.append(f'第五部分应有 {len(stories)} 条（与归档一致），当前识别到 {len(entries)} 条')
    for index, (entry, story) in enumerate(zip(entries, stories), 1):
        if entry['num'] != index:
            errors.append(f'第五部分第 {index} 条序号写成了 {entry["num"]}，须从 1 连续递增')
        if norm(entry['title']) != norm(story['title']):
            errors.append(f'第五部分第 {index} 条标题须原样保留：{story["title"]}（当前：{entry["title"]}）')
        if entry['brief'] != story['brief']:
            errors.append(f'第五部分第 {index} 条：快讯合集须用 <details> 折叠块，普通新闻用 **N. 标题**')
            continue
        text = '\n'.join(entry['lines'])
        if story['url'] and f'[央视原文]({story["url"]})' not in text:
            errors.append(f'第五部分第 {index} 条链接应为 [央视原文]({story["url"]})')
        if story['brief']:
            bullets = re.findall(r'(?m)^- \*\*(.+?)\*\*[：:]\s*(.*)$', text)
            if entry['count'] != len(story['briefs']) or len(bullets) != len(story['briefs']):
                errors.append(f'第五部分第 {index} 条快讯应为 {len(story["briefs"])} 条，'
                              f'标题写了 {entry["count"]} 条，实际列出 {len(bullets)} 条')
            for title, content in bullets:
                size = text_len(content)
                if not 25 <= size <= 70:
                    warns.append(f'快讯“{title[:16]}”缩写 {size} 字，应为 30 至 60 字')
        else:
            size = text_len(text)
            if not 54 <= size <= 198:
                warns.append(f'第五部分第 {index} 条缩写 {size} 字，应为 60 至 180 字')

    total = text_len(raw)
    if total > 11000:
        warns.append(f'全文 {total} 字，偏长，注意手机阅读长度')
    return report(fatal, errors, warns)


def report(fatal: list[str], errors: list[str], warns: list[str]) -> int:
    for item in fatal:
        print(f'FATAL: {item}')
    for item in errors:
        print(f'ERROR: {item}')
    for item in warns:
        print(f'WARN: {item}')
    verdict = '通过' if not fatal and not errors else '未通过'
    print(f'结果：{verdict}（FATAL {len(fatal)}，ERROR {len(errors)}，WARN {len(warns)}）')
    return 2 if fatal else 1 if errors else 0


def main(argv: list[str]) -> int:
    if len(argv) >= 2 and re.fullmatch(r'\d{8}', argv[1]):
        if argv[0] == 'facts' and len(argv) == 2:
            return cmd_facts(argv[1])
        if argv[0] == 'check' and len(argv) == 3:
            return cmd_check(argv[1], argv[2])
    print(__doc__.strip(), file=sys.stderr)
    return 64


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
