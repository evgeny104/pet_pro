"""
Тесты для страницы Dividends NVDA (MetaTrader).

Страница: https://www.metatrader.com/en/symbols/nasdaq/nvda/dividends
Таблица: Dividends per share, Dividend yield %, Payout ratio %
         (до текста Nvidia Corporation)

Формат проверки: каждое значение float/double, нули не допускаются (> 0).
"""

import re
import pytest
from playwright.sync_api import Browser, Page

URL = "https://www.metatrader.com/en/symbols/nasdaq/nvda/dividends"

FLOAT_PATTERN = re.compile(r"^\d+(\.\d+)?$")

# Метрики для проверки: (отображаемое имя, возможные ключи на сайте)
METRICS = [
    ("Dividends per share", ["Dividends per share", "Dividend per share", "Dividends Per Share"]),
    ("Dividend yield %",    ["Dividend yield %", "Dividend Yield %", "Dividend yield", "Yield %"]),
    ("Payout ratio %",      ["Payout ratio %", "Payout Ratio %", "Payout ratio", "Payout %"]),
]


# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------

def is_float_format(value: str) -> bool:
    """True если строка — положительное число float/double."""
    return bool(FLOAT_PATTERN.match(value.strip()))


def is_positive(value: str) -> bool:
    """True если значение строго больше 0."""
    try:
        return float(value.strip()) > 0
    except ValueError:
        return False


def assert_all_positive_floats(label: str, values: list[str]) -> None:
    """Проверяет все значения метрики: float формат и > 0."""
    assert values, f"[{label}] значения не найдены в таблице"
    for v in values:
        assert is_float_format(v), (
            f"[{label}] '{v}' — не соответствует формату float/double"
        )
        assert is_positive(v), (
            f"[{label}] '{v}' — нулевые значения недопустимы (должно быть > 0)"
        )


def _get(data: dict, *keys: str) -> tuple[str, list[str]]:
    """Возвращает (найденный ключ, список значений) или ('', []) если не найдено."""
    for k in keys:
        if k in data:
            return k, data[k]
    return "", []


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def dividends_data(browser: Browser) -> dict[str, list[str]]:
    """
    Открывает страницу Dividends NVDA, возвращает словарь
    label -> [col1, col2, ...] для метрик таблицы (до Nvidia Corporation).
    """
    page: Page = browser.new_page()
    page.goto(URL, wait_until="domcontentloaded", timeout=60_000)
    page.locator("text=Dividends per share").first.wait_for(timeout=15_000)
    page.wait_for_timeout(2000)

    raw: str = page.inner_text("body")
    page.close()

    stop = raw.find("Nvidia Corporation")
    block = raw[:stop] if stop > 0 else raw

    ds_start = block.find("Dividends per share")
    if ds_start >= 0:
        block = block[ds_start:]

    num_pat    = re.compile(r"^\d+(\.\d+)?$")
    year_pat   = re.compile(r"^\d{4}$")
    skip_words = {
        "Value", "TTM", "Financials", "ANNUAL", "QUARTERLY",
        "Annual", "Quarterly", "Ask", "Bid",
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
    }

    lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
    result: dict[str, list[str]] = {}
    i = 0
    while i < len(lines):
        label = lines[i]
        if num_pat.match(label) or year_pat.match(label) or label in skip_words:
            i += 1
            continue
        values: list[str] = []
        j = i + 1
        while j < len(lines) and (num_pat.match(lines[j]) or year_pat.match(lines[j])):
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
# Тесты
# ---------------------------------------------------------------------------

def test_dividends_page_loads(page: Page):
    """Страница Dividends открывается и метрика 'Dividends per share' видна."""
    page.goto(URL, wait_until="domcontentloaded", timeout=60_000)
    heading = page.locator("text=Dividends per share").first
    heading.wait_for(timeout=15_000)
    assert heading.is_visible(), "'Dividends per share' не найдена на странице"


@pytest.mark.parametrize("metric_name,keys", METRICS, ids=[m[0] for m in METRICS])
def test_metric_is_float(dividends_data: dict, metric_name: str, keys: list[str]):
    """Все колонки метрики: float/double > 0, нули недопустимы."""
    label, values = _get(dividends_data, *keys)
    assert values, f"{metric_name} не найден. Ключи: {list(dividends_data)[:8]}"
    assert_all_positive_floats(label, values)


def test_all_dividends_values_are_float(dividends_data: dict):
    """Сквозная проверка: все метрики таблицы Dividends — float/double > 0."""
    assert dividends_data, "Данные таблицы Dividends не были собраны"

    bad_format = [(k, v) for k, vs in dividends_data.items() for v in vs if not is_float_format(v)]
    bad_zero   = [(k, v) for k, vs in dividends_data.items() for v in vs if is_float_format(v) and not is_positive(v)]

    errors = []
    if bad_format:
        errors.append("Не соответствуют формату float/double:\n"
                      + "\n".join(f"  {k}: '{v}'" for k, v in bad_format))
    if bad_zero:
        errors.append("Нулевые значения (недопустимы):\n"
                      + "\n".join(f"  {k}: '{v}'" for k, v in bad_zero))

    assert not errors, f"Метрик: {len(dividends_data)}\n\n" + "\n\n".join(errors)
