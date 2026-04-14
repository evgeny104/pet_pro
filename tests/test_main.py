from src.main import Regions
from src.config import BASE_URL
import pytest


@pytest.mark.parametrize(
    "q,country_code,page_size,page",
    [
        ("Нов","ru", 5, 10)
    ]
)

def test_get_response(q, country_code, page_size, page):
    url = f"{BASE_URL}"

    # Создаём экземпляр класса с параметрами
    regions = Regions(
        url=url,
        q = q,
        country_code=country_code,
        page_size=page_size,
        page=page
    )

    # Получаем данные Json.
    data, status_code = regions.get_response()

    # Проверяем что данные не None
    assert data is not None
    # Проверяем статус код
    assert status_code == 200
    # Проверяем что в данных есть ключ 'total'
    assert 'total' in data

    assert data['total'] > 0
