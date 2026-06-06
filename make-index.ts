import fs from 'node:fs/promises';
import prettier from 'prettier';

const mdList = await fs.readdir('./news');

function printLink(name?: string | null) {
  if (!name) {
    return '';
  }

  return `[${name.replaceAll(/\.md$/g, '')}](./news/${name}.md)`;
}

function chunk<T>(store: T[], size: number) {
  const groupedList = [];
  for (let i = 0; i < store.length; i += size) {
    groupedList.push(store.slice(i, i + size));
  }

  return groupedList;
}

const groupedByMonth = mdList
  .filter((name) => /^\d{8}\.md$/.test(name))
  .map((name) => name.replaceAll(/\.md$/g, ''))
  .reduce(
    (g, it) => {
      const key = it.substring(0, 6); // 年月，如：202302
      const list = g[key] || [];
      list.push(it);
      g[key] = list;

      return g;
    },
    {} as Record<string, string[]>,
  );

let buf = '# 目录\n\n';

const mapGroupedByYearMonth = Object.entries(groupedByMonth).toSorted((a, b) => {
  return Number.parseInt(b[0]) - Number.parseInt(a[0]);
});

for (const [label, newsList] of mapGroupedByYearMonth) {
  buf += `## ${label}\n\n`;

  buf += '| 一 | 二 | 三 | 四 | 五 | 六 | 日 |\n';
  buf += '|---|---|---|---|---|---|---|\n';

  // 每月的列表
  const sortedNewsList: Array<string | null> = newsList.toSorted((a, b) => Number.parseInt(a) - Number.parseInt(b));

  // 在开头和结尾补充空单元格，对齐周一到周日的日历表格。
  {
    const fst = sortedNewsList[0] || '';

    const firstDay = new Date(
      Number.parseInt(fst.substring(0, 4)),
      Number.parseInt(fst.substring(4, 6)) - 1,
      Number.parseInt(fst.substring(6)),
      0,
      0,
      0,
    ).getDay();
    const leadingBlankCount = (firstDay + 6) % 7;

    for (let i = 0; i < leadingBlankCount; i++) {
      sortedNewsList.unshift(null);
    }

    while (sortedNewsList.length % 7 !== 0) {
      sortedNewsList.push(null);
    }
  }

  buf += chunk(sortedNewsList, 7)
    .map((dates) => `| ${dates.map(printLink).join(' | ')} |`)
    .map((row) => `${row}\n`)
    .join('');

  buf += '\n\n';
}

const formatted = await prettier.format(buf, { parser: 'markdown' });
await fs.writeFile('INDEX.md', formatted, 'utf-8');
console.log('updated');
