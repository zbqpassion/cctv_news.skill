#!/usr/bin/env python3
"""Keep the 30-day mainlines and 10-day hot words stable across daily reports.

Usage:
  topics.py show [--date YYYYMMDD]
  topics.py set --date YYYYMMDD --mainline 名称 ... --hotword '主题=同义词1|同义词2' ... [--reason 依据]

`set` registers what the report for that date uses. Compared with the last
registered date, at most one mainline and one hot word may be new unless
--reason explains the evidence. check-report.py compares the report against
this registration.
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_DIR = os.path.join(SKILL_DIR, 'state')
STATE_FILE = os.path.join(STATE_DIR, 'topics.json')
HISTORY_FILE = os.path.join(STATE_DIR, 'topics-history.jsonl')


def load_state() -> dict:
    try:
        with open(STATE_FILE, 'r', encoding='utf-8') as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return {}


def baseline_for(state: dict, date: str | None) -> dict:
    """The registration the given date should stay consistent with."""
    if not state:
        return {}
    if date and state.get('date') == date:
        return state.get('prev') or {}
    return {key: state.get(key) for key in ('date', 'mainlines', 'hotwords')}


def label_of(spec: str) -> str:
    return spec.split('=', 1)[0].strip()


def cmd_show(args) -> int:
    state = load_state()
    base = baseline_for(state, args.date)
    if not base:
        print('尚无登记记录：本期自行选定主线和热词，然后用 set 登记。')
        return 0
    print(f'上一期登记日期：{base["date"]}')
    print('长期主线（默认沿用，名称逐字不改）：')
    for index, name in enumerate(base.get('mainlines', []), 1):
        print(f'  {index}. {name}')
    print('近10日热词（默认沿用，含同义词）：')
    for spec in base.get('hotwords', []):
        print(f'  {spec}')
    until = f' --until {args.date}' if args.date else ''
    specs = ' '.join(f"'{spec}'" for spec in base.get('hotwords', []))
    print('沿用时的热词统计命令：')
    print(f'  python3 scripts/trend-analysis.py 10{until} {specs}')
    if state.get('date') == args.date:
        print(f'{args.date} 已登记过，当前登记：')
        print('  主线：' + '；'.join(state.get('mainlines', [])))
        print('  热词：' + '；'.join(state.get('hotwords', [])))
    return 0


def cmd_set(args) -> int:
    mainlines = [item.strip() for item in args.mainline if item.strip()]
    hotwords = [item.strip() for item in args.hotword if item.strip()]
    if not 2 <= len(mainlines) <= 4:
        print('长期主线需要 2 至 4 条。', file=sys.stderr)
        return 1
    if len(hotwords) != 4:
        print('近10日热词需要正好 4 个。', file=sys.stderr)
        return 1
    if len(set(mainlines)) != len(mainlines) or len({label_of(s) for s in hotwords}) != 4:
        print('主线或热词有重复。', file=sys.stderr)
        return 1
    for spec in hotwords:
        if '=' not in spec or not spec.split('=', 1)[1].strip():
            print(f'热词需写成 主题=同义词1|同义词2：{spec}', file=sys.stderr)
            return 1

    state = load_state()
    base = baseline_for(state, args.date)
    new_mainlines = [m for m in mainlines if m not in (base.get('mainlines') or [])]
    old_labels = {label_of(s) for s in (base.get('hotwords') or [])}
    new_hotwords = [label_of(s) for s in hotwords if label_of(s) not in old_labels]
    reason = (args.reason or '').strip()
    if base and (len(new_mainlines) > 1 or len(new_hotwords) > 1) and len(reason) < 10:
        print('与上一期相比更换过多，已拒绝登记。', file=sys.stderr)
        if new_mainlines:
            print('  新主线：' + '；'.join(new_mainlines), file=sys.stderr)
        if new_hotwords:
            print('  新热词：' + '；'.join(new_hotwords), file=sys.stderr)
        print('  每期最多新增 1 条主线和 1 个热词。名称只是换了说法的，请改回上一期的原名；'
              '确有国家级重大政策等依据时，加 --reason 写明依据。', file=sys.stderr)
        return 1

    record = {'date': args.date, 'mainlines': mainlines, 'hotwords': hotwords}
    if base:
        record['prev'] = base
    os.makedirs(STATE_DIR, exist_ok=True)
    tmp = STATE_FILE + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as handle:
        json.dump(record, handle, ensure_ascii=False, indent=2)
        handle.write('\n')
    os.replace(tmp, STATE_FILE)
    with open(HISTORY_FILE, 'a', encoding='utf-8') as handle:
        handle.write(json.dumps({
            'at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
            'date': args.date, 'mainlines': mainlines, 'hotwords': hotwords,
            'new_mainlines': new_mainlines, 'new_hotwords': new_hotwords, 'reason': reason,
        }, ensure_ascii=False) + '\n')
    print(f'已登记 {args.date}：主线 {len(mainlines)} 条（新增 {len(new_mainlines)}），'
          f'热词 4 个（新增 {len(new_hotwords)}）。')
    return 0


def date_arg(value: str) -> str:
    if not re.fullmatch(r'\d{8}', value):
        raise argparse.ArgumentTypeError('日期格式应为 YYYYMMDD')
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True)
    show = sub.add_parser('show')
    show.add_argument('--date', type=date_arg)
    show.set_defaults(func=cmd_show)
    setp = sub.add_parser('set')
    setp.add_argument('--date', type=date_arg, required=True)
    setp.add_argument('--mainline', action='append', default=[])
    setp.add_argument('--hotword', action='append', default=[])
    setp.add_argument('--reason')
    setp.set_defaults(func=cmd_set)
    args = parser.parse_args()
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
