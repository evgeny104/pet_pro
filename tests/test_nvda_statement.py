"""
Тесты для блока INCOME STATEMENT на странице NVDA (MetaTrader).

Страница: https://www.metatrader.com/en/symbols/nasdaq/nvda
Вкладка: Statement -> INCOME STATEMENT (до блока Nvidia Corporation)

Формат проверки: каждое значение float/double, допускается буква-суффикс K/M/B/T.
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


def assert_value(label: str, value: str) -> None:
    """Единая проверка: формат float + значение > 0."""
    assert is_float_format(value), (
        f"[{label}] '{value}' — не соответствует формату float/double (допускается буква K/M/B/T)"
    )
    assert is_positive(value), (
        f"[{label}] '{value}' — значение должно быть больше 0 (нули и отрицательные числа недопустимы)"
    )


# ---------------------------------------------------------------------------
# Fixture: один браузер на весь модуль, открываем страницу один раз
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def income_data(browser: Browser) -> dict[str, str]:
    """
    Открывает страницу NVDA, кликает по вкладке Statement,
    извлекает пары label → value из блока INCOME STATEMENT
    (текстовый парсинг innerText — надёжнее DOM-обхода для SPA).
    """
    page: Page = browser.new_page()
    page.goto(URL, wait_until="domcontentloaded", timeout=60_000)

    # Кликаем по вкладке Statement
    page.get_by_text("Statement", exact=True).first.click()

    # Ждём появления заголовка INCOME STATEMENT
    page.locator("text=INCOME STATEMENT").first.wait_for(timeout=15_000)
    page.wait_for_timeout(2000)

    # Берём весь текст страницы
    raw: str = page.inner_text("body")
    page.close()

    # Вырезаем блок INCOME STATEMENT … Nvidia Corporation
    is_marker = "INCOME STATEMENT"
    stop_marker = "Nvidia Corporation"

    start = raw.find(is_marker)
    if start < 0:
        return {}

    stop = raw.find(stop_marker, start)
    block = raw[start + len(is_marker): stop if stop > start else start + 8000]

    # Паттерн числового значения: необязательный «-», цифры, дробь, суффикс
    num_pat = re.compile(r"^-?\d+(\.\d+)?\s*[KMBT]?$", re.IGNORECASE)
    skip_words = {"Annual", "Quarterly", "TTM", "Q1", "Q2", "Q3", "Q4"}

    lines = [ln.strip() for ln in block.splitlines() if ln.strip()]

    result: dict[str, str] = {}
    i = 0
    while i < len(lines):
        label = lines[i]
        # Пропускаем строки, которые сами являются числом или служебным словом
        if num_pat.match(label) or label in skip_words or len(label) < 3:
            i += 1
            continue
        # Ищем первое числовое значение (или N/A) после лейбла
        if i + 1 < len(lines):
            value = lines[i + 1]
            if num_pat.match(value) or value == NA_VALUE:
                result[label] = value
                i += 2
                # Пропускаем дополнительные числовые колонки той же строки таблицы
                while i < len(lines) and (num_pat.match(lines[i]) or lines[i] == NA_VALUE):
                    i += 1
            else:
                i += 1
        else:
            i += 1

    return result


# ---------------------------------------------------------------------------
# Вспомогательная функция поиска значения по нескольким вариантам ключа
# ---------------------------------------------------------------------------

def _get(data: dict, *keys: str) -> tuple[str, str]:
    """Возвращает (найденный_ключ, значение) или ('', '') если не найдено."""
    for k in keys:
        if k in data:
            return k, data[k]
    return "", ""


# ---------------------------------------------------------------------------
# 1. Тест: вкладка Statement открывается и блок INCOME STATEMENT виден
# ---------------------------------------------------------------------------

def test_statement_tab_is_visible(page: Page):
    """Вкладка Statement кликабельна и раздел INCOME STATEMENT присутствует на странице."""
    page.goto(URL, wait_until="domcontentloaded", timeout=60_000)
    page.get_by_text("Statement", exact=True).first.click()
    page.wait_for_timeout(3000)

    income_heading = page.locator("text=INCOME STATEMENT").first
    income_heading.wait_for(timeout=15_000)
    assert income_heading.is_visible(), "Блок INCOME STATEMENT не виден после клика по Statement"


# ---------------------------------------------------------------------------
# 2. Тест: Total Revenue — float/double с опциональной буквой
# ---------------------------------------------------------------------------

def test_total_revenue_is_float(income_data: dict):
    """Total Revenue: float/double > 0, допускается буква-суффикс, нули и отрицательные — недопустимы."""
    label, value = _get(income_data, "Total Revenue", "Revenue", "Net Revenue", "Total revenue")
    assert value, f"Total Revenue не найден в INCOME STATEMENT. Найдено ключей: {list(income_data)[:10]}"
    assert_value(label, value)


# ---------------------------------------------------------------------------
# 3. Тест: Cost of Revenue — float/double с опциональной буквой
# ---------------------------------------------------------------------------

def test_cost_of_revenue_is_float(income_data: dict):
    """Cost of Revenue: float/double > 0, допускается буква-суффикс, нули и отрицательные — недопустимы."""
    label, value = _get(income_data, "Cost of Revenue", "Cost of Goods Sold", "COGS",
                        "Cost of revenue", "Cost of goods sold")
    assert value, f"Cost of Revenue не найден в INCOME STATEMENT. Найдено ключей: {list(income_data)[:10]}"
    assert_value(label, value)


# ---------------------------------------------------------------------------
# 4. Тест: Gross Profit — float/double с опциональной буквой
# ---------------------------------------------------------------------------

def test_gross_profit_is_float(income_data: dict):
    """Gross Profit: float/double > 0, допускается буква-суффикс, нули и отрицательные — недопустимы."""
    label, value = _get(income_data, "Gross Profit", "Gross profit", "Gross Income")
    assert value, f"Gross Profit не найден в INCOME STATEMENT. Найдено ключей: {list(income_data)[:10]}"
    assert_value(label, value)


# ---------------------------------------------------------------------------
# 5. Тест: Operating Expenses — float/double с опциональной буквой
# ---------------------------------------------------------------------------

def test_operating_expenses_is_float(income_data: dict):
    """Operating Expenses: float/double > 0, допускается буква-суффикс, нули и отрицательные — недопустимы."""
    label, value = _get(income_data, "Operating Expenses", "Total Operating Expenses",
                        "Operating expenses", "Total operating expenses")
    assert value, f"Operating Expenses не найден в INCOME STATEMENT. Найдено ключей: {list(income_data)[:10]}"
    assert_value(label, value)


# ---------------------------------------------------------------------------
# 6. Тест: Operating Income — float/double с опциональной буквой
# ---------------------------------------------------------------------------

def test_operating_income_is_float(income_data: dict):
    """Operating Income: float/double > 0, допускается буква-суффикс, нули и отрицательные — недопустимы."""
    label, value = _get(income_data, "Operating Income", "Income from Operations",
                        "Operating income", "Operating Income/Loss")
    assert value, f"Operating Income не найден в INCOME STATEMENT. Найдено ключей: {list(income_data)[:10]}"
    assert_value(label, value)


# ---------------------------------------------------------------------------
# 7. Тест: EBIT — float/double с опциональной буквой
# ---------------------------------------------------------------------------

def test_ebit_is_float(income_data: dict):
    """EBIT: float/double > 0, допускается буква-суффикс, нули и отрицательные — недопустимы."""
    label, value = _get(income_data, "EBIT", "Earnings Before Interest and Taxes")
    assert value, f"EBIT не найден в INCOME STATEMENT. Найдено ключей: {list(income_data)[:10]}"
    assert_value(label, value)


# ---------------------------------------------------------------------------
# 8. Тест: Net Income — float/double с опциональной буквой
# ---------------------------------------------------------------------------

def test_net_income_is_float(income_data: dict):
    """Net Income: float/double > 0, допускается буква-суффикс, нули и отрицательные — недопустимы."""
    label, value = _get(income_data, "Net Income", "Net income",
                        "Net Income Common Stockholders", "Net Profit")
    assert value, f"Net Income не найден в INCOME STATEMENT. Найдено ключей: {list(income_data)[:10]}"
    assert_value(label, value)


# ---------------------------------------------------------------------------
# 9. Тест: Basic EPS — float/double
# ---------------------------------------------------------------------------

def test_basic_eps_is_float(income_data: dict):
    """Basic EPS: float/double > 0, нули и отрицательные — недопустимы."""
    label, value = _get(income_data, "Basic EPS", "EPS Basic", "Basic earnings per share",
                        "Basic Earnings Per Share", "Basic EPS (reported)",
                        "Earnings per share, basic", "EPS (Basic)", "EPS basic",
                        "Basic earnings per share (Basic EPS)")
    assert value, f"Basic EPS не найден в INCOME STATEMENT. Найдено ключей: {list(income_data)[:10]}"
    assert_value(label, value)


# ---------------------------------------------------------------------------
# 10. Тест: Diluted EPS — float/double
# ---------------------------------------------------------------------------

def test_diluted_eps_is_float(income_data: dict):
    """Diluted EPS: float/double > 0, нули и отрицательные — недопустимы."""
    label, value = _get(income_data, "Diluted EPS", "EPS Diluted", "Diluted earnings per share",
                        "Diluted Earnings Per Share", "Diluted EPS (reported)",
                        "Earnings per share, diluted", "EPS (Diluted)", "EPS diluted",
                        "Diluted earnings per share (Diluted EPS)")
    assert value, f"Diluted EPS не найден в INCOME STATEMENT. Найдено ключей: {list(income_data)[:10]}"
    assert_value(label, value)


# ---------------------------------------------------------------------------
# 11. Тест: EBITDA — float/double с опциональной буквой
# ---------------------------------------------------------------------------

def test_ebitda_is_float(income_data: dict):
    """EBITDA: float/double > 0, допускается буква-суффикс, нули и отрицательные — недопустимы."""
    label, value = _get(income_data, "EBITDA", "Adjusted EBITDA")
    assert value, f"EBITDA не найден в INCOME STATEMENT. Найдено ключей: {list(income_data)[:10]}"
    assert_value(label, value)


# ---------------------------------------------------------------------------
# 12. Тест: все найденные значения блока — float/double (сквозная проверка)
# ---------------------------------------------------------------------------

def test_all_income_statement_values_are_float(income_data: dict):
    """Сквозная проверка всех значений INCOME STATEMENT:
    - формат float/double с опциональной буквой K/M/B/T
    - значение строго больше 0 (нули и отрицательные числа недопустимы)
    - N/A (—) допускается как отсутствие данных."""
    assert income_data, "Данные INCOME STATEMENT не были собраны"

    bad_format = {k: v for k, v in income_data.items() if not is_float_format(v)}
    bad_value  = {k: v for k, v in income_data.items() if is_float_format(v) and not is_positive(v)}

    errors = []
    if bad_format:
        errors.append(
            "Не соответствуют формату float/double:\n"
            + "\n".join(f"  {k}: '{v}'" for k, v in bad_format.items())
        )
    if bad_value:
        errors.append(
            "Нулевые или отрицательные значения (недопустимы):\n"
            + "\n".join(f"  {k}: '{v}'" for k, v in bad_value.items())
        )

    assert not errors, (
        f"Всего собрано метрик: {len(income_data)}\n" + "\n\n".join(errors)
    )
