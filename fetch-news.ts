import process from 'node:process';

import { fetchNews } from './_fetch-news.ts';

function parseDateArg(dateArg: string) {
  if (!/^\d{8}$/.test(dateArg)) {
    throw new Error('日期参数必须是 YYYYMMDD 格式，例如 20260503');
  }

  const year = Number(dateArg.slice(0, 4));
  const month = Number(dateArg.slice(4, 6));
  const day = Number(dateArg.slice(6, 8));

  return new Date(Date.UTC(year, month - 1, day, 0, 0, 0));
}

const today = new Date(); // 本地时间
const dateArg = process.argv[2];

// UTC+8 时间
const cnToday = new Date(
  Date.UTC(
    today.getUTCFullYear(),
    today.getUTCMonth(),
    today.getUTCDate(),
    today.getUTCHours(),
    today.getUTCMinutes() + 480,
    today.getUTCSeconds(),
  ),
);

const targetDate = dateArg ? parseDateArg(dateArg) : cnToday;

// 获取指定日期，未指定时获取当天的数据
fetchNews(targetDate);
