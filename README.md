# pet_pro — Автотесты MetaTrader

Проект содержит Playwright-тесты для проверки финансовых данных и новостей на сайте [metatrader.com](https://www.metatrader.com).

## Тесты

| Файл | Страница | Что проверяется |
|---|---|---|
| `tests/test_nvda_statement.py` | [NVDA Statement](https://www.metatrader.com/en/symbols/nasdaq/nvda) | Все значения блока INCOME STATEMENT — формат float, > 0, не отрицательные |
| `tests/test_nvda_dividends.py` | [NVDA Dividends](https://www.metatrader.com/en/symbols/nasdaq/nvda/dividends) | Dividends per share, Dividend yield %, Payout ratio % — формат float, > 0 |
| `tests/test_news_time.py` | [News](https://www.metatrader.com/en/news) | Время публикации каждой статьи: формат HH:MM и не старше 4 часов |

## Зависимости

- Python 3.14+
- pytest
- pytest-playwright
- allure-pytest
- Allure CLI ([инструкция по установке](https://allurereport.org/docs/install/))

Установка зависимостей:

```powershell
.\.venv\Scripts\python.exe -m pip install pytest pytest-playwright allure-pytest
.\.venv\Scripts\python.exe -m playwright install chromium
```

## Запуск тестов и генерация отчёта

**1. Перейти в корень проекта:**

```powershell
cd "C:\Users\eprok\OneDrive\Desktop\pet_pro"
```

**2. Очистить старые результаты и отчёт:**

```powershell
Remove-Item -Recurse -Force allure-results, allure-report -ErrorAction SilentlyContinue
```

**3. Запустить все тесты и сохранить результаты:**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/ -v --alluredir=allure-results
```

**4. Сгенерировать HTML-отчёт:**

```powershell
allure generate allure-results --clean -o allure-report
```

**5. Открыть отчёт в браузере:**

```powershell
allure open allure-report
```

## Структура проекта

```
pet_pro/
├── tests/
│   ├── test_nvda_statement.py   # INCOME STATEMENT проверки
│   ├── test_nvda_dividends.py   # Dividends проверки
│   └── test_news_time.py        # News время публикации
├── src/
│   └── main.py
├── .github/
│   └── workflows/
│       └── run.yml              # CI/CD GitHub Actions
├── pytest.ini
└── README.md
```
