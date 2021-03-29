"""
Модуль, содержащий обработчиков :)
"""
# Импорт из сторонних библиотек
from flask import request, abort, jsonify
from functools import partial
from dateutil import parser

from datetime import datetime, timezone
from collections import namedtuple
# Импорт модулей
from shop_api import app
from shop_api.models import *


def str_to_date(string, format_str='%H:%M'):
    """
    Возвращает объект datetime, полученный из строки(string) заданного формата(format).
    По умолчанию format="%H:%M"
    :param string: Строка времени
    :param format_str:  Формат времени строки
    :return: datetime.datetime
    """
    return datetime.strptime(string, format_str)


def time_intersection(order, courier):
    """
    Проверяет пересекаются ли временные промежутки  работы курьера(courier) и время доставки заказа (order)
    :param courier: Курьер, для которого идет поиск подходящих заказов
    :param order: Заказ, проверяющийся на соответствие
    :return: True если есть пересечения по времени, иначе False
    """

    Time = namedtuple('Time', ['start', 'end'])
    courier_time = []
    delivery_time = []

    for work_h in courier.working_hours:
        courier_time.append(Time(*map(str_to_date, work_h.hours.split('-'))))
    for del_h in order.delivery_hours:
        delivery_time.append(Time(*map(str_to_date, del_h.hours.split('-'))))

    for courier in courier_time:
        for order in delivery_time:
            if courier.start < order.end and courier.end > order.start:
                return True
    return False


def check_order_validity(courier, order):
    """
    Проверяет на соответсвие заказ и курьера. Возвращает True, если курьер может взять этот заказ, иначе False
    :param courier: Курьер - экземпляр класса Couriers
    :param order: Заказ - экземпляр класса Orders
    :return: bool
    """
    threshold = 10 if courier.courier_type == 'foot' else 15 if courier.courier_type == 'bike' else 50
    if order.region not in {region.region_num for region in courier.regions} or order.weight > threshold \
            or not time_intersection(order, courier):
        return False
    return True


def update_courier(courier):
    """
    Обновляет рейтинг курьера после каждого выполенного курьером заказа.
    Обновляет з/п после завершения развоза, при условии что курьер доставил хотя-бы один заказ из развоза.
    :param courier: Курьер, для которого обновляются данные
    :return: None
    """
    if courier.at_least_one and not courier.current_orders:
        courier.earnings += 500 * (2 if courier.courier_type == 'foot' else 5 if courier.courier_type == 'bike' else 9)
        courier.at_least_one = False
    if courier.earnings != 0:
        min_average = float('inf')
        for region in courier.regions:
            orders_by_cour_in_reg = db.session.query(OrdersHistory.delivery_time). \
                filter_by(courier_id=courier.courier_id, order_region=region.region_num).all()
            if orders_by_cour_in_reg:
                region_average = 0
                for i in orders_by_cour_in_reg:
                    region_average += i[0]

                region_average /= len(orders_by_cour_in_reg)
                if region_average < min_average:
                    min_average = region_average

        courier.rating = round((60 * 60 - min(min_average, 60 * 60)) / (60 * 60) * 5, 2)


@app.route('/couriers', methods=['POST'])
def post_courier():
    """
        Проводим валидацию данных - уникальный id и наличие всех обязательных полей:
    1) Все данные верны:
         -добавляем всех курьеров в базу данных
         -возвращем id всех добавленных заказов и status 201 'Created'
    2) Не все заказы прошли валидацию:
         -возвращаем id всех "плохих" курьеров и status 400 'Bad Request'
    """
    data = request.get_json()['data']
    validation_error = []
    couriers = []
    for cour in data:
        if set(cour.keys()) != {'courier_id', 'courier_type', 'regions', 'working_hours'} \
                or db.session.query(Couriers.courier_id).filter_by(courier_id=cour['courier_id']).scalar():
            validation_error.append({'id': cour['courier_id']})
        else:
            courier = Couriers(courier_id=cour['courier_id'], courier_type=cour['courier_type'])
            courier.regions.extend([Regions.safe_init(region_num=region) for region in cour['regions']])
            courier.working_hours.extend([WorkHours.safe_init(hours=cw_hour) for cw_hour in cour['working_hours']])
            couriers.append({'id': cour['courier_id']})
            db.session.add(courier)
    if validation_error:
        db.session.rollback()
        return jsonify({'validation_error': {'couriers': validation_error}}), 400
    db.session.commit()
    return jsonify({'couriers': couriers}), 201


@app.route('/couriers/<id_c>', methods=['PATCH', 'GET'])
def show_courier(id_c: int):
    """
    1) Если получен PATCH запрос:
        Проводим валидацию пререданной информации, в случае передачи неописанных полей возвращаем  Bad Request 400,
        иначе - изменяем информацию о данном курьере  и возвращаем JSON,
        содержащий актуальную информацию о курьере, status code 200
    2) Если получен GET запрос:
        Возвращаем JSON, содержащий актуальную информацию о курьере, status code 200
    """
    cour = db.session.query(Couriers).filter_by(courier_id=id_c).first()
    if cour:
        if request.method == 'PATCH':
            data = request.get_json()
            if set(data.keys()).issubset({'courier_type', 'regions', 'working_hours'}):
                for key in data.keys():
                    if key == 'regions':
                        cour.regions.clear()
                        cour.regions.extend([Regions.safe_init(region_num=i) for i in data['regions']])
                    elif key == 'working_hours':
                        cour.working_hours.clear()
                        cour.working_hours.extend([WorkHours.safe_init(hours=i) for i in data['working_hours']])
                    else:
                        cour.courier_type = data['courier_type']

                # Проверяем нужно ли снять заказы с курьера
                for order in cour.current_orders:
                    if not check_order_validity(cour, order):
                        order.available = True
                        cour.current_orders.remove(order)

                cour.current_orders.sort(key=lambda x: x.weight)
                threshold = 10 if cour.courier_type == 'foot' else 15 if cour.courier_type == 'bike' else 50

                while sum([order.weight for order in cour.current_orders]) > threshold:
                    cour.current_orders.pop().available = True

                update_courier(cour)
                db.session.commit()
                return cour.to_json(), 200
            else:
                abort(400)
        elif request.method == 'GET':
            return cour.to_json(), 200
    else:
        abort(404)


@app.route('/orders', methods=['POST'])
def post_orders():
    """
    Проводим валидацию данных:
           1) Все данные верны:
                -добавляем все заказы в базу данных
                -возвращем id всех добавленных заказов и status 201 'Created'
           2) Не все заказы прошли валидацию:
                -возвращаем id всех "плохих" заказаов и status 400 'Bad Request'
    """
    data = request.get_json()['data']
    validation_error = []
    orders = []
    for order in data:
        if set(order.keys()) != {'order_id', 'region', 'delivery_hours', 'weight'} \
                or order['weight'] < 0.01 or order['weight'] > 50 \
                or db.session.query(Orders.order_id).filter_by(order_id=order['order_id']).scalar():
            validation_error.append({'id': order['order_id']})
        else:
            new_order = Orders(order_id=order['order_id'], weight=order['weight'], region=order['region'])
            new_order.delivery_hours.extend([DeliveryHours.safe_init(hours=hour) for hour in order['delivery_hours']])
            db.session.add(new_order)
            orders.append({'id': order['order_id']})
    if validation_error:
        db.session.rollback()
        return jsonify({'validation_error': {'orders': validation_error}}), 400
    db.session.commit()
    return jsonify({'orders': orders}), 201


@app.route('/orders/assign', methods=['POST'])
def assign_orders():
    """
    Назначает заказы курьеру исходя из: 1) максимальной грузоподъемности курьера и веса заказов
                                        2) часов работы курьера и часов доставки заказов
                                        3) региона заказа и рабочих регионов курьера
    Возвращает словарь, содержащий id НОВЫХ назначенных заказов, а также время назначения,
    если до этого у курьера не было активных заказов.
    :return: dict
    """
    cour_id = request.get_json()['courier_id']
    if not Couriers.query.filter_by(courier_id=cour_id).scalar():
        abort(400)
    else:
        cour = Couriers.query.filter_by(courier_id=cour_id).first()
        relevant_orders = db.session.query(Orders).filter(Orders.available,
                                                          Orders.region.in_(
                                                              (region.region_num for region in cour.regions))). \
            order_by(Orders.weight).all()

        relevant_time_intersection = partial(time_intersection, courier=cour)

        relevant_orders = filter(relevant_time_intersection, relevant_orders)

        if cour.current_orders:
            threshold = 10 if cour.courier_type == 'foot' else 15 if cour.courier_type == 'bike' else 50 - \
                                                                sum([order.weight for order in cour.current_orders])
        else:
            threshold = 10 if cour.courier_type == 'foot' else 15 if cour.courier_type == 'bike' else 50
        orders = []
        for order in relevant_orders:
            if threshold > order.weight:
                threshold -= order.weight
                order.available = False
                cour.current_orders.append(order)
                orders.append({'id': order.order_id})
            else:
                break

        if not cour.assign_time:
            cour.assign_time = datetime.strftime(datetime.now(timezone.utc), "%Y-%m-%dT%H:%M:%S.42Z")
            db.session.commit()
            return {'orders': orders, 'assign_time': cour.assign_time}
        db.session.commit()
        return {'orders': orders}


@app.route('/orders/complete', methods=['POST'])
def complete_orders():
    """
    Принимает идентификатор курьера и заказа, а также время заверщшения заказа
    При прохождении валидации заказа сохраняется в истории заказов и удаляется из "активных".
    В случае заверщения курьером развоза, для него пересчитывается рейтинг и заработок
    :return: dict
    """
    data = request.get_json()
    cour = db.session.query(Couriers).filter_by(courier_id=data['courier_id']).first()
    if not cour or data['order_id'] not in {order.order_id for order in cour.current_orders}:
        abort(400)
    else:
        order = db.session.query(Orders).filter_by(order_id=data['order_id']).first()
        delivery_time = (parser.isoparse(data['complete_time']) - parser.isoparse(cour.assign_time)).seconds
        cour.assign_time = data['complete_time']
        completed_order = OrdersHistory(order_id=order.order_id, order_region=order.region,
                                        courier_id=cour.courier_id,
                                        delivery_time=delivery_time)

        cour.at_least_one = True
        db.session.add(completed_order)
        db.session.delete(order)
        db.session.commit()
        update_courier(cour)
        db.session.commit()

        return {'order_id': completed_order.order_id}, 200


@app.route('/delete/all/records', methods=['POST'])
def delete_all():
    """
    Если в теле запроса присутствует поле 'delete_all', производит удаление записей из ВСЕХ таблиц.
    :return: None
    """
    if request.get_json()['delete_all']:
        Couriers.query.delete()
        Orders.query.delete()
        Regions.query.delete()
        WorkHours.query.delete()
        DeliveryHours.query.delete()
        OrdersHistory.query.delete()
        db.session.query(del_hours).delete()
        db.session.query(courier_hours).delete()
        db.session.query(courier_regions).delete()
        db.session.commit()
        return {'message': 'All records deleted successfully!'}
    else:
        abort(400)
