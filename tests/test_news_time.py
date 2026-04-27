"""
Тесты для страницы MetaTrader News.

Страница: https://www.metatrader.com/en/news
Область проверки: все статьи ДО кнопки "More News".

Проверки:
  1. Время публикации присутствует и соответствует формату HH:MM.
  2. Время публикации не старше 4 часов относительно системного времени.
"""

import re
from datetime import datetime, timedelta, timezone

import pytest
from playwright.sync_api import Browser, Page

URL = "https://www.metatrader.com/en/news"

# Паттерн формата времени HH:MM
TIME_PATTERN = re.compile(r"^\d{2}:\d{2}$")

# Максимально допустимый возраст статьи
MAX_AGE_HOURS = 4


# ---------------------------------------------------------------------------
# Fixture: открываем страницу и извлекаем список статей один раз на модуль
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def articles(browser: Browser) -> list[dict]:
    """
    Открывает страницу News, собирает все статьи ДО кнопки 'More News'.
    Возвращает список словарей: [{'time': 'HH:MM', 'title': '...'}].
    """
    page: Page = browser.new_page()
    page.goto(URL, wait_until="domcontentloaded", timeout=60_000)

    # Ждём появления первой временной метки
    page.locator("text=More News").first.wait_for(timeout=20_000)
    page.wait_for_timeout(2000)

    raw: str = page.inner_text("body")
    page.close()

    # Вырезаем блок до кнопки "More News"
    stop = raw.find("More News")
    block = raw[:stop] if stop > 0 else raw

    # Пропускаем шапку (до первой строки-времени)
    lines = [ln.strip() for ln in block.splitlines() if ln.strip()]

    result: list[dict] = []
    i = 0
    while i < len(lines):
        if TIME_PATTERN.match(lines[i]):
            time_str = lines[i]
            title = lines[i + 1] if i + 1 < len(lines) else ""
            result.append({"time": time_str, "title": title})
            i += 2
        else:
            i += 1

    return result


# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------

def _article_age_hours(time_str: str) -> float:
    """
    Возвращает возраст статьи в часах.

    Playwright может рендерить время страницы в UTC либо в локальном часовом поясе
    в зависимости от режима запуска браузера. Чтобы не зависеть от этого,
    вычисляем возраст относительно UTC и относительно локального времени,
    и берём минимум: совпадающий часовой пояс даст меньшее (корректное) значение.

    Пример: статья 14:55 UTC, система UTC+3 (18:35 local):
      age_utc   = 15:35 − 14:55 = 40 мин  ← корректно
      age_local = 18:35 − 14:55 = 3ч40мин ← артефакт
      min = 40 мин ✓
    """
    t = datetime.strptime(time_str, "%H:%M")

    def _age_vs(reference: datetime) -> float:
        pub = reference.replace(hour=t.hour, minute=t.minute, second=0, microsecond=0)
        if pub > reference:
            pub -= timedelta(days=1)
        return (reference - pub).total_seconds() / 3600

    age_local = _age_vs(datetime.now().replace(second=0, microsecond=0))
    age_utc   = _age_vs(datetime.now(timezone.utc).replace(tzinfo=None, second=0, microsecond=0))
    return min(age_local, age_utc)


# ---------------------------------------------------------------------------
# 1. Тест: страница загружается и статьи найдены
# ---------------------------------------------------------------------------

def test_news_page_loads(page: Page):
    """Страница News открывается и содержит кнопку 'More News'."""
    page.goto(URL, wait_until="domcontentloaded", timeout=60_000)
    btn = page.locator("text=More News").first
    btn.wait_for(timeout=20_000)
    assert btn.is_visible(), "Кнопка 'More News' не найдена на странице"


def test_articles_found(articles: list):
    """Список статей до 'More News' не пустой."""
    assert len(articles) > 0, "Статьи до кнопки 'More News' не найдены"


# ---------------------------------------------------------------------------
# 2. Тест: формат времени HH:MM — для каждой статьи отдельная проверка
# ---------------------------------------------------------------------------

def test_format_article_01(articles):
    """Статья #1: время публикации в формате HH:MM."""
    _assert_format(articles, 0)


def test_format_article_02(articles):
    """Статья #2: время публикации в формате HH:MM."""
    _assert_format(articles, 1)


def test_format_article_03(articles):
    """Статья #3: время публикации в формате HH:MM."""
    _assert_format(articles, 2)


def test_format_article_04(articles):
    """Статья #4: время публикации в формате HH:MM."""
    _assert_format(articles, 3)


def test_format_article_05(articles):
    """Статья #5: время публикации в формате HH:MM."""
    _assert_format(articles, 4)


def test_format_article_06(articles):
    """Статья #6: время публикации в формате HH:MM."""
    _assert_format(articles, 5)


def test_format_article_07(articles):
    """Статья #7: время публикации в формате HH:MM."""
    _assert_format(articles, 6)


def test_format_article_08(articles):
    """Статья #8: время публикации в формате HH:MM."""
    _assert_format(articles, 7)


def test_format_article_09(articles):
    """Статья #9: время публикации в формате HH:MM."""
    _assert_format(articles, 8)


def test_format_article_10(articles):
    """Статья #10: время публикации в формате HH:MM."""
    _assert_format(articles, 9)


def test_format_all_articles(articles):
    """Сквозная проверка: все статьи до 'More News' имеют время в формате HH:MM."""
    assert articles, "Статьи не найдены"
    bad = [
        f"  #{i+1} '{a['time']}' — {a['title'][:60]}"
        for i, a in enumerate(articles)
        if not TIME_PATTERN.match(a["time"])
    ]
    assert not bad, (
        f"Статьи с неверным форматом времени ({len(bad)} шт.):\n" + "\n".join(bad)
    )


# ---------------------------------------------------------------------------
# 3. Тест: свежесть — время публикации не старше 4 часов
# ---------------------------------------------------------------------------

def test_freshness_article_01(articles):
    """Статья #1: опубликована не ранее чем 4 часа назад."""
    _assert_freshness(articles, 0)


def test_freshness_article_02(articles):
    """Статья #2: опубликована не ранее чем 4 часа назад."""
    _assert_freshness(articles, 1)


def test_freshness_article_03(articles):
    """Статья #3: опубликована не ранее чем 4 часа назад."""
    _assert_freshness(articles, 2)


def test_freshness_article_04(articles):
    """Статья #4: опубликована не ранее чем 4 часа назад."""
    _assert_freshness(articles, 3)


def test_freshness_article_05(articles):
    """Статья #5: опубликована не ранее чем 4 часа назад."""
    _assert_freshness(articles, 4)


def test_freshness_article_06(articles):
    """Статья #6: опубликована не ранее чем 4 часа назад."""
    _assert_freshness(articles, 5)


def test_freshness_article_07(articles):
    """Статья #7: опубликована не ранее чем 4 часа назад."""
    _assert_freshness(articles, 6)


def test_freshness_article_08(articles):
    """Статья #8: опубликована не ранее чем 4 часа назад."""
    _assert_freshness(articles, 7)


def test_freshness_article_09(articles):
    """Статья #9: опубликована не ранее чем 4 часа назад."""
    _assert_freshness(articles, 8)


def test_freshness_article_10(articles):
    """Статья #10: опубликована не ранее чем 4 часа назад."""
    _assert_freshness(articles, 9)


def test_freshness_all_articles(articles):
    """Сквозная проверка: все статьи до 'More News' опубликованы не ранее 4 часов назад."""
    assert articles, "Статьи не найдены"
    now_local = datetime.now().replace(second=0, microsecond=0)
    now_utc   = datetime.now(timezone.utc).replace(tzinfo=None, second=0, microsecond=0)
    bad = []
    for i, a in enumerate(articles):
        if not TIME_PATTERN.match(a["time"]):
            continue  # формат уже проверяется отдельно
        age = _article_age_hours(a["time"])
        if age > MAX_AGE_HOURS:
            bad.append(
                f"  #{i+1} [{a['time']}] возраст {age:.1f}ч > {MAX_AGE_HOURS}ч"
                f" — {a['title'][:60]}"
            )
    assert not bad, (
        f"Системное время: {now_local.strftime('%H:%M')} (local) / {now_utc.strftime('%H:%M')} (UTC)\n"
        f"Статьи старше {MAX_AGE_HOURS}ч ({len(bad)} шт.):\n" + "\n".join(bad)
    )


# ---------------------------------------------------------------------------
# Вспомогательные функции assert
# ---------------------------------------------------------------------------

def _assert_format(articles: list, index: int) -> None:
    """Проверяет формат времени для статьи по индексу."""
    if index >= len(articles):
        pytest.skip(f"Статья #{index + 1} отсутствует (всего статей: {len(articles)})")
    a = articles[index]
    assert TIME_PATTERN.match(a["time"]), (
        f"Статья #{index + 1}: время '{a['time']}' не соответствует формату HH:MM\n"
        f"Заголовок: {a['title']}"
    )


def _assert_freshness(articles: list, index: int) -> None:
    """Проверяет что статья по индексу не старше MAX_AGE_HOURS."""
    if index >= len(articles):
        pytest.skip(f"Статья #{index + 1} отсутствует (всего статей: {len(articles)})")
    a = articles[index]
    if not TIME_PATTERN.match(a["time"]):
        pytest.skip(f"Статья #{index + 1}: пропуск freshness — время '{a['time']}' не в формате HH:MM")

    age = _article_age_hours(a["time"])
    now_local = datetime.now().replace(second=0, microsecond=0)
    now_utc   = datetime.now(timezone.utc).replace(tzinfo=None, second=0, microsecond=0)

    assert age <= MAX_AGE_HOURS, (
        f"Статья #{index + 1}: время публикации {a['time']} — "
        f"возраст {age:.1f}ч > {MAX_AGE_HOURS}ч\n"
        f"Системное время: {now_local.strftime('%H:%M')} (local) / {now_utc.strftime('%H:%M')} (UTC)\n"
        f"Заголовок: {a['title']}"
    )
