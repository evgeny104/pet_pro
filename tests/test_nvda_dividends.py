"""
Тесты для страницы Dividends NVDA (MetaTrader).

Страница: https://www.metatrader.com/en/symbols/nasdaq/nvda/dividends
Таблица: Dividends per share, Dividend yield %, Payout ratio %
         (до текста NVIDIA Corporation)

Формат проверки: каждое значение float/double.
Нули не допускаются (значение > 0).
"""

import re
import pytest
from playwright.sync_api import Browser, Page

URL = "https://www.metatrader.com/en/symbols/nasdaq/nvda/dividends"

# Только положительные числа: цифры + необязательная дробная часть
FLOAT_PATTERN = re.compile(r"^\d+(\.\d+)?$")


def is_float_format(value: str) -> bool:
    """Возвращает True если строка является числом float/double."""
    return bool(FLOAT_PATTERN.match(value.strip()))


def is_positive(value: str) -> bool:
    """Возвращает True если значение строго больше 0."""
    try:
        return float(value.strip()) > 0
    except ValueError:
        return False


def assert_all_positive_floats(label: str, values: list[str]) -> None:
    """Проверяет что все значения метрики: float формат и > 0."""
    assert values, f"[{label}] значения не найдены в таблице"
    for v in values:
        assert is_float_format(v), (
            f"[{label}] '{v}' — не соответствует формату float/double"
        )
        assert is_positive(v), (
            f"[{label}] '{v}' — нулевые значения недопустимы (должно быть > 0)"
        )


# ---------------------------------------------------------------------------
# Fixture: открываем страницу Dividends один раз на весь модуль
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def dividends_data(browser: Browser) -> dict[str, list[str]]:
    """
    Открывает страницу Dividends NVDA, извлекает все значения для каждой
    метрики из таблицы (до блока NVIDIA Corporation).
    Возвращает словарь: label -> [value1, value2, ...].
    """
    page: Page = browser.new_page()
    page.goto(URL, wait_until="domcontentloaded", timeout=60_000)

    # Ждём появления хотя бы одной метрики
    page.locator("text=Dividends per share").first.wait_for(timeout=15_000)
    page.wait_for_timeout(2000)

    raw: str = page.inner_text("body")
    page.close()

    # Вырезаем блок до NVIDIA Corporation
    stop_marker = "Nvidia Corporation"
    stop = raw.find(stop_marker)
    block = raw[:stop] if stop > 0 else raw

    # Паттерн числового значения (только положительные числа без суффиксов)
    num_pat = re.compile(r"^\d+(\.\d+)?$")
    skip_words = {
        "Value", "TTM", "Financials", "ANNUAL", "QUARTERLY",
        "Annual", "Quarterly", "Ask", "Bid", "Apr", "Jan", "Feb",
        "Mar", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
    }

    # Сужаем блок до строки "Dividends per share" как начала таблицы
    ds_marker = "Dividends per share"
    ds_start = block.find(ds_marker)
    if ds_start >= 0:
        block = block[ds_start:]

    lines = [ln.strip() for ln in block.splitlines() if ln.strip()]

    result: dict[str, list[str]] = {}
    i = 0
    while i < len(lines):
        label = lines[i]
        # Пропускаем числа, годы (4 цифры) и служебные слова
        if num_pat.match(label) or re.match(r"^\d{4}$", label) or label in skip_words:
            i += 1
            continue
        # Собираем все следующие числовые значения как колонки этой метрики
        values = []
        j = i + 1
        while j < len(lines) and (num_pat.match(lines[j]) or re.match(r"^\d{4}$", lines[j])):
            if num_pat.match(lines[j]):
                values.append(lines[j])
            j += 1
        if values:
            result[label] = values
            i = j
        else:
            i += 1

    return result


# ---------------------------------------------------------------------------
# 1. Тест: страница Dividends загружается и таблица отображается
# ---------------------------------------------------------------------------

def test_dividends_page_loads(page: Page):
    """Страница Dividends открывается и метрика 'Dividends per share' видна."""
    page.goto(URL, wait_until="domcontentloaded", timeout=60_000)
    heading = page.locator("text=Dividends per share").first
    heading.wait_for(timeout=15_000)
    assert heading.is_visible(), "'Dividends per share' не найдена на странице"


# ---------------------------------------------------------------------------
# 2. Тест: Dividends per share — все значения float > 0
# ---------------------------------------------------------------------------

def test_dividends_per_share_is_float(dividends_data: dict):
    """Dividends per share: все значения float/double, нули недопустимы."""
    label, values = _get(dividends_data,
                         "Dividends per share", "Dividend per share",
                         "Dividends Per Share")
    assert_all_positive_floats(label, values)


# ---------------------------------------------------------------------------
# 3. Тест: последнее значение Dividends per share (TTM) float > 0
# ---------------------------------------------------------------------------

def test_dividends_per_share_latest_is_float(dividends_data: dict):
    """Dividends per share (последнее/TTM значение): float > 0."""
    label, values = _get(dividends_data,
                         "Dividends per share", "Dividend per share",
                         "Dividends Per Share")
    assert values, f"Dividends per share не найден. Ключи: {list(dividends_data)[:8]}"
    latest = values[-1]
    assert is_float_format(latest), f"[{label}] последнее значение '{latest}' — не float"
    assert is_positive(latest),     f"[{label}] последнее значение '{latest}' — нулевое (недопустимо)"


# ---------------------------------------------------------------------------
# 4. Тест: Dividend yield % — все значения float > 0
# ---------------------------------------------------------------------------

def test_dividend_yield_is_float(dividends_data: dict):
    """Dividend yield %: все значения float/double, нули недопустимы."""
    label, values = _get(dividends_data,
                         "Dividend yield %", "Dividend Yield %",
                         "Dividend yield", "Yield %")
    assert_all_positive_floats(label, values)


# ---------------------------------------------------------------------------
# 5. Тест: последнее значение Dividend yield % (TTM) float > 0
# ---------------------------------------------------------------------------

def test_dividend_yield_latest_is_float(dividends_data: dict):
    """Dividend yield % (последнее/TTM значение): float > 0."""
    label, values = _get(dividends_data,
                         "Dividend yield %", "Dividend Yield %",
                         "Dividend yield", "Yield %")
    assert values, f"Dividend yield % не найден. Ключи: {list(dividends_data)[:8]}"
    latest = values[-1]
    assert is_float_format(latest), f"[{label}] последнее значение '{latest}' — не float"
    assert is_positive(latest),     f"[{label}] последнее значение '{latest}' — нулевое (недопустимо)"


# ---------------------------------------------------------------------------
# 6. Тест: Payout ratio % — все значения float > 0
# ---------------------------------------------------------------------------

def test_payout_ratio_is_float(dividends_data: dict):
    """Payout ratio %: все значения float/double, нули недопустимы."""
    label, values = _get(dividends_data,
                         "Payout ratio %", "Payout Ratio %",
                         "Payout ratio", "Payout %")
    assert_all_positive_floats(label, values)


# ---------------------------------------------------------------------------
# 7. Тест: последнее значение Payout ratio % (TTM) float > 0
# ---------------------------------------------------------------------------

def test_payout_ratio_latest_is_float(dividends_data: dict):
    """Payout ratio % (последнее/TTM значение): float > 0."""
    label, values = _get(dividends_data,
                         "Payout ratio %", "Payout Ratio %",
                         "Payout ratio", "Payout %")
    assert values, f"Payout ratio % не найден. Ключи: {list(dividends_data)[:8]}"
    latest = values[-1]
    assert is_float_format(latest), f"[{label}] последнее значение '{latest}' — не float"
    assert is_positive(latest),     f"[{label}] последнее значение '{latest}' — нулевое (недопустимо)"


# ---------------------------------------------------------------------------
# 8. Тест: сквозная проверка — все значения таблицы float > 0
# ---------------------------------------------------------------------------

def test_all_dividends_values_are_float(dividends_data: dict):
    """Сквозная проверка: каждое значение таблицы Dividends float/double > 0.
    Нулевые значения недопустимы."""
    assert dividends_data, "Данные таблицы Dividends не были собраны"

    bad_format  = {k: v for k, vs in dividends_data.items()
                   for v in vs if not is_float_format(v)}
    bad_zero    = {k: v for k, vs in dividends_data.items()
                   for v in vs if is_float_format(v) and not is_positive(v)}

    errors = []
    if bad_format:
        errors.append(
            "Не соответствуют формату float/double:\n"
            + "\n".join(f"  {k}: '{v}'" for k, v in bad_format.items())
        )
    if bad_zero:
        errors.append(
            "Нулевые значения (недопустимы):\n"
            + "\n".join(f"  {k}: '{v}'" for k, v in bad_zero.items())
        )

    assert not errors, (
        f"Всего метрик: {len(dividends_data)}\n" + "\n\n".join(errors)
    )


# ---------------------------------------------------------------------------
# Вспомогательная функция поиска по нескольким вариантам ключа
# ---------------------------------------------------------------------------

def _get(data: dict, *keys: str) -> tuple[str, list[str]]:
    """Возвращает (найденный_ключ, список_значений) или ('', []) если не найдено."""
    for k in keys:
        if k in data:
            return k, data[k]
    return "", []
