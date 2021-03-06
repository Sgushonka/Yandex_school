"""
REST API сервис для интернет магазина.
Функционал:
    -Добавление курьера в БД
    -Изменение информации о курьере
    -Добавление заказа в БД
    -Назначение заказов курьеру
    -Расчет рейтинга и заработка курьера
"""
# Импорт модулей
from shop_api import app

if __name__ == '__main__':
    app.run(debug=True)
