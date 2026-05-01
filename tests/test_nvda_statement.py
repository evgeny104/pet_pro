"""
Тесты для блока INCOME STATEMENT на странице NVDA (MetaTrader).

Страница: https://www.metatrader.com/en/symbols/nasdaq/nvda
Вкладка: Statement -> INCOME STATEMENT (до блока Nvidia Corporation)

Формат проверки: каждое значение float/double, допускается буква-суффикс K/M/B/T.
Проверяются ВСЕ колонки (2020, 2021, 2022, 2023, 2024, 2025, TTM).
Не допускаются: отрицательные числа и нули.
"""

import re
import pytest
from playwright.sync_api import Browser, Page

URL = "https://www.metatrader.com/en/symbols/nasdaq/nvda"

FLOAT_PATTERN = re.compile(r"^\d+(\.\d+)?\s*[KMBT]?$", re.IGNORECASE)
NA_VALUE = "\u2014"

# Метрики для проверки: (отображаемое имя, возможные ключи на сайте)
METRICS = [
    ("Total Revenue",      ["Total Revenue", "Revenue", "Net Revenue", "Total revenue"]),
    ("Cost of Revenue",    ["Cost of Revenue", "Cost of Goods Sold", "COGS",
                            "Cost of revenue", "Cost of goods sold"]),
    ("Gross Profit",       ["Gross Profit", "Gross profit", "Gross Income"]),
    ("Operating Expenses", ["Operating Expenses", "Total Operating Expenses",
                            "Operating expenses", "Total operating expenses"]),
    ("Operating Income",   ["Operating Income", "Income from Operations",
                            "Operating income", "Operating Income/Loss"]),
    ("EBIT",               ["EBIT", "Earnings Before Interest and Taxes"]),
    ("Net Income",         ["Net Income", "Net income",
                            "Net Income Common Stockholders", "Net Profit"]),
    ("Basic EPS",          ["Basic EPS", "EPS Basic", "Basic earnings per share",
                            "Basic Earnings Per Share", "Basic EPS (reported)",
                            "Earnings per share, basic", "EPS (Basic)", "EPS basic",
                            "Basic earnings per share (Basic EPS)"]),
    ("Diluted EPS",        ["Diluted EPS", "EPS Diluted", "Diluted earnings per share",
                            "Diluted Earnings Per Share", "Diluted EPS (reported)",
                            "Earnings per share, diluted", "EPS (Diluted)", "EPS diluted",
                            "Diluted earnings per share (Diluted EPS)"]),
    ("EBITDA",             ["EBITDA", "Adjusted EBITDA"]),
]


# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------

def is_float_format(value: str) -> bool:
    """Формат float/double с опциональным суффиксом K/M/B/T. N/A допустим."""
    v = value.strip()
    return v == NA_VALUE or bool(FLOAT_PATTERN.match(v))


def is_positive(value: str) -> bool:
    """True если значение > 0 (N/A считается допустимым)."""
    v = value.strip()
    if v == NA_VALUE:
        return True
    numeric = re.sub(r"\s*[KMBT]$", "", v, flags=re.IGNORECASE).strip()
    try:
        return float(numeric) > 0
    except ValueError:
        return False


def assert_all_values(label: str, values: list[str]) -> None:
    """Проверяет все колонки метрики: формат float и значение > 0."""
    assert values, f"[{label}] значения не найдены в таблице"
    for v in values:
        assert is_float_format(v), (
            f"[{label}] '{v}' — не соответствует формату float/double (допускается K/M/B/T)"
        )
        assert is_positive(v), (
            f"[{label}] '{v}' — должно быть > 0 (нули и отрицательные недопустимы)"
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
def income_data(browser: Browser) -> dict[str, list[str]]:
    """
    Открывает страницу NVDA, кликает по вкладке Statement,
    возвращает словарь label -> [col1, col2, ...] для всех метрик блока
    INCOME STATEMENT (до строки Nvidia Corporation).
    """
    page: Page = browser.new_page()
    page.goto(URL, wait_until="domcontentloaded", timeout=60_000)
    page.get_by_text("Statement", exact=True).first.click()
    page.locator("text=INCOME STATEMENT").first.wait_for(timeout=15_000)
    page.wait_for_timeout(2000)

    raw: str = page.inner_text("body")
    page.close()

    start = raw.find("INCOME STATEMENT")
    if start < 0:
        return {}
    stop  = raw.find("Nvidia Corporation", start)
    block = raw[start + len("INCOME STATEMENT"): stop if stop > start else start + 8000]

    num_pat    = re.compile(r"^-?\d+(\.\d+)?\s*[KMBT]?$", re.IGNORECASE)
    year_pat   = re.compile(r"^\d{4}$")
    skip_words = {"Annual", "Quarterly", "TTM", "Q1", "Q2", "Q3", "Q4",
                  "BALANCE SHEET", "CASH FLOW", "INCOME STATEMENT"}

    lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
    result: dict[str, list[str]] = {}
    i = 0
    while i < len(lines):
        label = lines[i]
        if num_pat.match(label) or year_pat.match(label) or label in skip_words or len(label) < 3:
            i += 1
            continue
        values: list[str] = []
        j = i + 1
        while j < len(lines):
            token = lines[j]
            if year_pat.match(token) or token == "TTM":
                j += 1
                continue
            if num_pat.match(token) or token == NA_VALUE:
                values.append(token)
                j += 1
            else:
                break
        if values:
            result[label] = values
            i = j
        else:
            i += 1

    return result


# ---------------------------------------------------------------------------
# Тесты
# ---------------------------------------------------------------------------

def test_statement_tab_is_visible(page: Page):
    """Вкладка Statement кликабельна и блок INCOME STATEMENT присутствует."""
    page.goto(URL, wait_until="domcontentloaded", timeout=60_000)
    page.get_by_text("Statement", exact=True).first.click()
    page.wait_for_timeout(3000)
    heading = page.locator("text=INCOME STATEMENT").first
    heading.wait_for(timeout=15_000)
    assert heading.is_visible(), "Блок INCOME STATEMENT не виден после клика по Statement"


@pytest.mark.parametrize("metric_name,keys", METRICS, ids=[m[0] for m in METRICS])
def test_metric_is_float(income_data: dict, metric_name: str, keys: list[str]):
    """Все колонки метрики: float/double > 0, допускается суффикс K/M/B/T."""
    label, values = _get(income_data, *keys)
    assert values, f"{metric_name} не найден в INCOME STATEMENT. Ключи: {list(income_data)[:10]}"
    assert_all_values(label, values)


def test_all_income_statement_values_are_float(income_data: dict):
    """Сквозная проверка: все метрики, все колонки — float/double > 0."""
    assert income_data, "Данные INCOME STATEMENT не были собраны"

    bad_format: list[str] = []
    bad_value:  list[str] = []

    for metric, values in income_data.items():
        for v in values:
            if not is_float_format(v):
                bad_format.append(f"  {metric}: '{v}'")
            elif not is_positive(v):
                bad_value.append(f"  {metric}: '{v}'")

    errors = []
    if bad_format:
        errors.append("Не соответствуют формату float/double:\n" + "\n".join(bad_format))
    if bad_value:
        errors.append("Нулевые или отрицательные значения:\n" + "\n".join(bad_value))

    assert not errors, f"Метрик: {len(income_data)}\n\n" + "\n\n".join(errors)
