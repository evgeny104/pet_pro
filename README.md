# Pet Project

Небольшой Python-проект для запроса списка регионов через API `2gis`.

## Структура

```text
pet_project/
|-- src/
|   |-- __init__.py
|   |-- main.py
|   `-- config.py
|-- tests/
|   `-- test_main.py
|-- .gitignore
|-- pytest.ini
`-- README.md
```

## Установка

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install pytest requests
```

## Запуск тестов

```powershell
pytest
```

## Примечания

- `src/config.py` хранит локальную конфигурацию и не добавляется в Git.
- Основная логика находится в `src/main.py`.
- Тест API находится в `tests/test_main.py`.
