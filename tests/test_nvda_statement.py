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

# Только положительные числа (без знака минус), необязательная буква-суффикс
FLOAT_PATTERN = re.compile(r"^\d+(\.\d+)?\s*[KMBT]?$", re.IGNORECASE)
NA_VALUE = "\u2014"


def is_float_format(value: str) -> bool:
    """Формат float/double с опциональной буквой-суффиксом K/M/B/T. N/A допустим."""
    v = value.strip()
    if v == NA_VALUE:
        return True
    return bool(FLOAT_PATTERN.match(v))


def is_positive(value: str) -> bool:
    """Возвращает True если значение больше нуля (не ноль и не отрицательное)."""
    v = value.strip()
    if v == NA_VALUE:
        return True
    numeric = re.sub(r"\s*[KMBT]$", "", v, flags=re.IGNORECASE).strip()
    try:
        return float(numeric) > 0
    except ValueError:
        return False


def assert_all_values(label: str, values: list[str]) -> None:
    """Проверяет ВСЕ колонки метрики: формат float + значение > 0."""
    assert values, f"[{label}] значения не найдены в таблице"
    for v in values:
        assert is_float_format(v), (
            f"[{label}] '{v}' — не соответствует формату float/double "
            f"(допускается буква K/M/B/T)"
        )
        assert is_positive(v), (
            f"[{label}] '{v}' — значение должно быть больше 0 "
            f"(нули и отрицательные числа недопустимы)"
        )


# ---------------------------------------------------------------------------
# Fixture: один браузер на весь модуль, открываем страницу один раз
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def income_data(browser: Browser) -> dict[str, list[str]]:
    """
    Открывает страницу NVDA, кликает по вкладке Statement,
    извлекает пары label → [value_col1, value_col2, ...] из блока INCOME STATEMENT.
    Собирает ВСЕ числовые колонки (2020, 2021 ... TTM) для каждой метрики.
    """
    page: Page = browser.new_page()
    page.goto(URL, wait_until="domcontentloaded", timeout=60_000)

    page.get_by_text("Statement", exact=True).first.click()
    page.locator("text=INCOME STATEMENT").first.wait_for(timeout=15_000)
    page.wait_for_timeout(2000)

    raw: str = page.inner_text("body")
    page.close()

    # Вырезаем блок INCOME STATEMENT … Nvidia Corporation
    is_marker  = "INCOME STATEMENT"
    stop_marker = "Nvidia Corporation"

    start = raw.find(is_marker)
    if start < 0:
        return {}

    stop  = raw.find(stop_marker, start)
    block = raw[start + len(is_marker): stop if stop > start else start + 8000]

    # Паттерн числового значения: необязательный «-», цифры, дробь, суффикс
    num_pat   = re.compile(r"^-?\d+(\.\d+)?\s*[KMBT]?$", re.IGNORECASE)
    skip_words = {"Annual", "Quarterly", "TTM", "Q1", "Q2", "Q3", "Q4",
                  "BALANCE SHEET", "CASH FLOW", "INCOME STATEMENT"}

    lines = [ln.strip() for ln in block.splitlines() if ln.strip()]

    result: dict[str, list[str]] = {}
    i = 0
    while i < len(lines):
        label = lines[i]
        # Пропускаем числа, 4-значные годы, служебные слова и короткие токены
        if (num_pat.match(label) or re.match(r"^\d{4}$", label)
                or label in skip_words or len(label) < 3):
            i += 1
            continue
        # Собираем ВСЕ следующие числовые значения как колонки этой метрики
        values: list[str] = []
        j = i + 1
        while j < len(lines):
            token = lines[j]
            if re.match(r"^\d{4}$", token):   # год-заголовок колонки — пропускаем
                j += 1
                continue
            if token == "TTM":                 # заголовок TTM — пропускаем
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
# Вспомогательная функция поиска по нескольким вариантам ключа
# ---------------------------------------------------------------------------

def _get(data: dict, *keys: str) -> tuple[str, list[str]]:
    """Возвращает (найденный_ключ, список_значений) или ('', []) если не найдено."""
    for k in keys:
        if k in data:
            return k, data[k]
    return "", []


# ---------------------------------------------------------------------------
# 1. Тест: вкладка Statement открывается и блок INCOME STATEMENT виден
# ---------------------------------------------------------------------------

def test_statement_tab_is_visible(page: Page):
    """Вкладка Statement кликабельна и раздел INCOME STATEMENT присутствует."""
    page.goto(URL, wait_until="domcontentloaded", timeout=60_000)
    page.get_by_text("Statement", exact=True).first.click()
    page.wait_for_timeout(3000)
    heading = page.locator("text=INCOME STATEMENT").first
    heading.wait_for(timeout=15_000)
    assert heading.is_visible(), "Блок INCOME STATEMENT не виден после клика по Statement"


# ---------------------------------------------------------------------------
# 2. Total Revenue — все колонки float/double > 0
# ---------------------------------------------------------------------------

def test_total_revenue_is_float(income_data: dict):
    """Total Revenue: все колонки float/double > 0."""
    label, values = _get(income_data, "Total Revenue", "Revenue", "Net Revenue", "Total revenue")
    assert values, f"Total Revenue не найден. Ключи: {list(income_data)[:10]}"
    assert_all_values(label, values)


# ---------------------------------------------------------------------------
# 3. Cost of Revenue — все колонки float/double > 0
# ---------------------------------------------------------------------------

def test_cost_of_revenue_is_float(income_data: dict):
    """Cost of Revenue: все колонки float/double > 0."""
    label, values = _get(income_data, "Cost of Revenue", "Cost of Goods Sold", "COGS",
                         "Cost of revenue", "Cost of goods sold")
    assert values, f"Cost of Revenue не найден. Ключи: {list(income_data)[:10]}"
    assert_all_values(label, values)


# ---------------------------------------------------------------------------
# 4. Gross Profit — все колонки float/double > 0
# ---------------------------------------------------------------------------

def test_gross_profit_is_float(income_data: dict):
    """Gross Profit: все колонки float/double > 0."""
    label, values = _get(income_data, "Gross Profit", "Gross profit", "Gross Income")
    assert values, f"Gross Profit не найден. Ключи: {list(income_data)[:10]}"
    assert_all_values(label, values)


# ---------------------------------------------------------------------------
# 5. Operating Expenses — все колонки float/double > 0
# ---------------------------------------------------------------------------

def test_operating_expenses_is_float(income_data: dict):
    """Operating Expenses: все колонки float/double > 0."""
    label, values = _get(income_data, "Operating Expenses", "Total Operating Expenses",
                         "Operating expenses", "Total operating expenses")
    assert values, f"Operating Expenses не найден. Ключи: {list(income_data)[:10]}"
    assert_all_values(label, values)


# ---------------------------------------------------------------------------
# 6. Operating Income — все колонки float/double > 0
# ---------------------------------------------------------------------------

def test_operating_income_is_float(income_data: dict):
    """Operating Income: все колонки float/double > 0."""
    label, values = _get(income_data, "Operating Income", "Income from Operations",
                         "Operating income", "Operating Income/Loss")
    assert values, f"Operating Income не найден. Ключи: {list(income_data)[:10]}"
    assert_all_values(label, values)


# ---------------------------------------------------------------------------
# 7. EBIT — все колонки float/double > 0
# ---------------------------------------------------------------------------

def test_ebit_is_float(income_data: dict):
    """EBIT: все колонки float/double > 0."""
    label, values = _get(income_data, "EBIT", "Earnings Before Interest and Taxes")
    assert values, f"EBIT не найден. Ключи: {list(income_data)[:10]}"
    assert_all_values(label, values)


# ---------------------------------------------------------------------------
# 8. Net Income — все колонки float/double > 0
# ---------------------------------------------------------------------------

def test_net_income_is_float(income_data: dict):
    """Net Income: все колонки float/double > 0."""
    label, values = _get(income_data, "Net Income", "Net income",
                         "Net Income Common Stockholders", "Net Profit")
    assert values, f"Net Income не найден. Ключи: {list(income_data)[:10]}"
    assert_all_values(label, values)


# ---------------------------------------------------------------------------
# 9. Basic EPS — все колонки float/double > 0
# ---------------------------------------------------------------------------

def test_basic_eps_is_float(income_data: dict):
    """Basic EPS: все колонки float/double > 0."""
    label, values = _get(income_data, "Basic EPS", "EPS Basic", "Basic earnings per share",
                         "Basic Earnings Per Share", "Basic EPS (reported)",
                         "Earnings per share, basic", "EPS (Basic)", "EPS basic",
                         "Basic earnings per share (Basic EPS)")
    assert values, f"Basic EPS не найден. Ключи: {list(income_data)[:10]}"
    assert_all_values(label, values)


# ---------------------------------------------------------------------------
# 10. Diluted EPS — все колонки float/double > 0
# ---------------------------------------------------------------------------

def test_diluted_eps_is_float(income_data: dict):
    """Diluted EPS: все колонки float/double > 0."""
    label, values = _get(income_data, "Diluted EPS", "EPS Diluted", "Diluted earnings per share",
                         "Diluted Earnings Per Share", "Diluted EPS (reported)",
                         "Earnings per share, diluted", "EPS (Diluted)", "EPS diluted",
                         "Diluted earnings per share (Diluted EPS)")
    assert values, f"Diluted EPS не найден. Ключи: {list(income_data)[:10]}"
    assert_all_values(label, values)


# ---------------------------------------------------------------------------
# 11. EBITDA — все колонки float/double > 0
# ---------------------------------------------------------------------------

def test_ebitda_is_float(income_data: dict):
    """EBITDA: все колонки float/double > 0."""
    label, values = _get(income_data, "EBITDA", "Adjusted EBITDA")
    assert values, f"EBITDA не найден. Ключи: {list(income_data)[:10]}"
    assert_all_values(label, values)


# ---------------------------------------------------------------------------
# 12. Сквозная проверка — все метрики, все колонки
# ---------------------------------------------------------------------------

def test_all_income_statement_values_are_float(income_data: dict):
    """Сквозная проверка всех значений INCOME STATEMENT (все колонки):
    - формат float/double с опциональной буквой K/M/B/T
    - значение строго больше 0 (нули и отрицательные числа недопустимы)
    - N/A (—) допускается как отсутствие данных."""
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
        errors.append(
            "Не соответствуют формату float/double:\n" + "\n".join(bad_format)
        )
    if bad_value:
        errors.append(
            "Нулевые или отрицательные значения (недопустимы):\n" + "\n".join(bad_value)
        )

    assert not errors, (
        f"Всего собрано метрик: {len(income_data)}\n" + "\n\n".join(errors)
    )
