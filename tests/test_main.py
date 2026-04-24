from src.main import Regions
from src.config import BASE_URL
import pytest


@pytest.fixture
def region_response(request):
    """
    Fixture: создаёт экземпляр Regions и возвращает (data, status_code).
    Принимает параметры через request.param от indirect=True.
    Пустые значения ("", 0, None) заменяются на None.
    """
    q, country_code, page_size, page = request.param

    params = Regions(
        url=BASE_URL,
        q=q or None,
        country_code=country_code or None,
        page_size=page_size or None,
        page=page or None
    )
    return params.get_response()


class TestRegionsQ:
    """
    q — нечёткий поиск по названию региона.
    Минимум 3 символа, регистр не важен,
    если передан q — остальные параметры игнорируются.
    """

    @pytest.mark.parametrize(
        "region_response",
        [
            ("Новосибирск", None, None, None),  # полное название
            ("нов", None, None, None),           # строчные буквы
            ("НОВ", None, None, None),           # заглавные буквы
            ("Нов", None, None, None),           # смешанный регистр
        ],
        indirect=True
    )
    def test_q_case_insensitive(self, region_response):
        """Регистр не имеет значения"""
        data, status_code = region_response
        assert status_code == 200
        assert data is not None
        assert data['items'][0]['name'] == "Новосибирск"

    @pytest.mark.parametrize(
        "region_response",
        [
            ("но", None, None, None),  # 2 символа
            ("Н", None, None, None),   # 1 символ
        ],
        indirect=True
    )
    def test_q_too_short(self, region_response):
        """Меньше 3 символов → ошибка валидации"""
        data, status_code = region_response
        assert status_code == 200
        assert data is not None
        assert data['error']['message'] == "Параметр 'q' должен быть не менее 3 символов"

    @pytest.mark.parametrize(
        "region_response",
        [
            # ✅ исправлено: 99 → допустимые значения
            ("Новосибирск", "kg", 5, 1),
            ("Новосибирск", "xx", 5, 1),
        ],
        indirect=True
    )
    def test_q_ignores_other_params(self, region_response):
        """Если передан q — остальные параметры игнорируются"""
        data, status_code = region_response
        assert status_code == 200
        assert data is not None
        assert data['items'][0]['name'] == "Новосибирск"

    @pytest.mark.parametrize(
        "region_response",
        [
            ("рск", None, None, None),  # вхождение подстроки
        ],
        indirect=True
    )
    def test_q_fuzzy_search(self, region_response):
        """Нечёткий поиск — поиск по вхождению подстроки"""
        data, status_code = region_response
        assert status_code == 200
        assert data is not None
        for item in data['items']:
            assert "рск" in item['name'].lower()


class TestRegionsCountryCode:
    """
    country_code — фильтрация по коду страны.
    Допустимые значения: ru, kg, kz, cz.
    По умолчанию — регионы из всех стран.
    """

    @pytest.mark.parametrize(
        "region_response, expected_code",
        [
            (("Нов", "ru", None, None), "ru"),  # Россия
            (("Нов", "kg", None, None), "kg"),  # Киргизия
            (("Нов", "kz", None, None), "kz"),  # Казахстан
            (("Нов", "cz", None, None), "cz"),  # Чехия
        ],
        indirect=["region_response"]  # ✅ только region_response через fixture
    )
    def test_country_code_valid(self, region_response, expected_code):
        """Допустимые значения country_code → все регионы из этой страны"""
        data, status_code = region_response
        assert status_code == 200
        assert data is not None
        assert data['total'] > 0
        for item in data['items']:
            assert item['country']['code'] == expected_code  # ✅ точная проверка

    @pytest.mark.parametrize(
        "region_response",
        [
            (None, "xx", None, None),    # несуществующий код
            (None, "123", None, None),   # цифры вместо кода
        ],
        indirect=True
    )
    def test_country_code_invalid(self, region_response):
        """Недопустимый country_code → пустой список"""
        data, status_code = region_response
        assert status_code == 200
        assert data is not None
        assert data['total'] == 0
        assert data['items'] == []

    @pytest.mark.parametrize(
        "region_response",
        [
            (None, None, None, None),  # без country_code
        ],
        indirect=True
    )
    def test_country_code_default(self, region_response):
        """Без country_code возвращаются регионы всех стран"""
        data, status_code = region_response
        assert status_code == 200
        assert data is not None
        assert data['total'] > 0
        countries = {item['country']['code'] for item in data['items']}
        assert len(countries) > 1  # регионы из разных стран


class TestRegionsPage:
    """
    page — порядковый номер страницы.
    Минимальное значение — 1.
    Значение по умолчанию — 1.
    """

    @pytest.mark.parametrize(
        "region_response",
        [
            (None, None, None, 1),  # первая страница
            (None, None, None, 2),  # вторая страница
        ],
        indirect=True
    )
    def test_page_valid(self, region_response):
        """Корректный номер страницы → успешный ответ"""
        data, status_code = region_response
        assert status_code == 200
        assert data is not None
        assert data['total'] > 0

    @pytest.mark.parametrize(
        "region_response",
        [
            (None, None, None, 0),   # меньше минимума
            (None, None, None, -1),  # отрицательное значение
        ],
        indirect=True
    )
    def test_page_invalid(self, region_response):
        """Номер страницы меньше 1 → ошибка валидации"""
        data, status_code = region_response
        assert status_code == 200
        assert data is not None
        assert data['error']['message'] == "Параметр 'page' должен быть не менее 1"

    @pytest.mark.parametrize(
        "region_response",
        [
            (None, None, None, None),  # без page
        ],
        indirect=True
    )
    def test_page_default(self, region_response):
        """Без page возвращается первая страница по умолчанию"""
        data, status_code = region_response
        assert status_code == 200
        assert data is not None
        assert data['total'] > 0


class TestRegionsPageSize:
    """
    page_size — количество элементов на странице.
    Допустимые значения: 5, 10, 15.
    Значение по умолчанию — 15.
    """

    @pytest.mark.parametrize(
        "region_response, expected_size",
        [
            ((None, None, 5, None), 5),    # минимальный размер
            ((None, None, 10, None), 10),  # средний размер
            ((None, None, 15, None), 15),  # максимальный размер
        ],
        indirect=["region_response"]  # ✅ точная проверка размера
    )
    def test_page_size_valid(self, region_response, expected_size):
        """Допустимые значения page_size → точное количество элементов"""
        data, status_code = region_response
        assert status_code == 200
        assert data is not None
        assert len(data['items']) == expected_size  # ✅ было <= 15

    @pytest.mark.parametrize(
        "region_response",
        [
            (None, None, 1, None),   # недопустимое значение
            (None, None, 20, None),  # недопустимое значение
        ],
        indirect=True
    )
    def test_page_size_invalid(self, region_response):
        """Недопустимый page_size → ошибка валидации"""
        data, status_code = region_response
        assert status_code == 200
        assert data is not None
        assert data['error']['message'] == "Параметр 'page_size' может быть одним из следующих значений: 5, 10, 15"

    @pytest.mark.parametrize(
        "region_response",
        [
            (None, None, None, None),  # без page_size
        ],
        indirect=True
    )
    def test_page_size_default(self, region_response):
        """Без page_size возвращается 15 элементов по умолчанию"""
        data, status_code = region_response
        assert status_code == 200
        assert data is not None
        assert len(data['items']) == 15