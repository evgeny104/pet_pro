import requests

class Regions:
    """
    Инициализащция:
        функции: data и status_code = None= в случае ошибки вызова except в get_response.
    """
    def __init__(self, url=None,q=None, country_code=None, page_size=None, page=None):
        self.url = url
        self.q = q
        self.country_code = country_code
        self.page_size = page_size
        self.page = page
        self.data = None
        self.status_code = None

    def get_response(self):
        res = None  # none ← для except ValueError мог безопасно обратиться к res

        try:
            # Инициннируем список для параметров вызова.
            params = {}

            if self.q:
                params['q'] = self.q
            if self.country_code:
                params['country_code'] = self.country_code
            if self.page_size is not None:
                params['page_size'] = self.page_size
            if self.page is not None:
                params['page'] = self.page

            # Выполняет GET к API с параметрами.
            res = requests.get(self.url, params=params)
            status_code = res.status_code

            # Сохраняем данные в переменной класса.
            if status_code == 200:
                data = res.json()
                self.data = data
                self.status_code = status_code
                return data, status_code
            else:
                print(f"\n\nОшибка: статус != 200 == {status_code}")
                self.status_code = status_code
                return None, status_code

        except requests.exceptions.RequestException as e:
            print(f"Ошибка выполнения запроса: {e}")
            self.status_code = None
            return None, None

        except ValueError as e:
            print(f"Ошибка парсинга JSON: {e}")
            status_code = res.status_code if res is not None else None
            self.status_code = status_code
            return None, status_code

    def get_data(self):
        """Возвращает загруженные данные."""
        return self.data

    def get_status(self):
        """Возвращает статус код последнего запроса."""
        return self.status_code


if __name__ == '__main__':
    regions = Regions()