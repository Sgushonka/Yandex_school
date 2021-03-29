"""
Модуль, содержащий модели :)
"""
# Импорт модулей
from shop_api import db

courier_regions = db.Table('courier_regions',
                           db.Column('region_num', db.Integer, db.ForeignKey('regions.region_num')),
                           db.Column('courier_id', db.Integer, db.ForeignKey('couriers.courier_id')))

courier_hours = db.Table('courier_hours',
                         db.Column('work_hours', db.Integer, db.ForeignKey('work_hours.hours')),
                         db.Column('courier_id', db.Integer, db.ForeignKey('couriers.courier_id')))

del_hours = db.Table('order_hours',
                     db.Column('delivery_hours', db.Integer, db.ForeignKey('delivery_hours.hours')),
                     db.Column('order_id', db.Integer, db.ForeignKey('orders.order_id')))


class Couriers(db.Model):
    courier_id = db.Column(db.Integer, nullable=False, primary_key=True)
    courier_type = db.Column(db.String, nullable=False)
    regions = db.relationship('Regions', secondary=courier_regions, backref=db.backref('couriers', lazy='subquery'),
                              lazy='subquery')
    working_hours = db.relationship('WorkHours', secondary=courier_hours, backref=db.backref('couriers', lazy=True),
                                    lazy='subquery')
    earnings = db.Column(db.Integer, default=0)
    rating = db.Column(db.Float)
    current_orders = db.relationship('Orders', backref='courier', lazy=True)
    assign_time = db.Column(db.String)
    at_least_one = db.Column(db.Boolean, default=False)

    def to_json(self):
        """
        Функция возвращяющая актуальную информацию о курьере в виде словаря.
        :return: dict
        """
        regions = [r.region_num for r in self.regions]
        work_hours = [w.hours for w in self.working_hours]
        cour_info = {'courier_id': self.courier_id, 'courier_type': self.courier_type, 'regions': regions,
                     'working_hours': work_hours, 'rating': self.rating, 'earnings': self.earnings}
        if self.rating is None:
            del cour_info['rating']
        return cour_info


class Orders(db.Model):
    order_id = db.Column(db.Integer, unique=True, nullable=False, primary_key=True)
    weight = db.Column(db.Float, nullable=False)
    region = db.Column(db.Integer, nullable=False)
    delivery_hours = db.relationship('DeliveryHours', secondary=del_hours, backref=db.backref('orders'), lazy=True)
    available = db.Column(db.Boolean, default=True)
    courier_id = db.Column(db.Integer, db.ForeignKey('couriers.courier_id'))


class Regions(db.Model):
    region_num = db.Column(db.Integer, unique=True, primary_key=True)

    @classmethod
    def safe_init(cls, **kwargs):
        if not db.session.query(Regions.region_num).filter_by(region_num=kwargs['region_num']).scalar():
            new_inst = cls(region_num=kwargs['region_num'])
            return new_inst
        else:
            return db.session.query(Regions).filter_by(region_num=kwargs['region_num']).first()


class WorkHours(db.Model):
    __tablename__ = 'work_hours'
    hours = db.Column(db.String, primary_key=True)

    @classmethod
    def safe_init(cls, **kwargs):
        if not db.session.query(WorkHours.hours).filter_by(hours=kwargs['hours']).scalar():
            new_inst = cls(hours=kwargs['hours'])
            return new_inst
        else:
            return db.session.query(WorkHours).filter_by(hours=kwargs['hours']).first()


class DeliveryHours(db.Model):
    __tablename__ = 'delivery_hours'
    hours = db.Column(db.String, primary_key=True)

    @classmethod
    def safe_init(cls, **kwargs):
        if not db.session.query(DeliveryHours.hours).filter_by(hours=kwargs['hours']).scalar():
            new_inst = cls(hours=kwargs['hours'])
            return new_inst
        else:
            return db.session.query(DeliveryHours).filter_by(hours=kwargs['hours']).first()


class OrdersHistory(db.Model):
    order_id = db.Column(db.Integer, primary_key=True)
    order_region = db.Column(db.Integer)
    courier_id = db.Column(db.Integer)
    delivery_time = db.Column(db.Integer)
