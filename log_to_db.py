import psutil
import time
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy import Table, Column, Integer, String, MetaData, ForeignKey, DateTime, Float
from sqlalchemy import orm
from sqlalchemy.sql import func

DB_CONNECT = 'sqlite:///db3.db'


# DB_CONNECT ='sqlite:///:memory:'


class Values(object):
    def __init__(self, param_id, value, timestamp):
        self.param_id = param_id
        self.value = value
        self.timestamp = timestamp

    def __repr__(self):
        return "Value('%s')" % (self.value)


class Params(object):
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return "Params('%s')" % (self.name)


class Db_log:
    def __init__(self, db_connector):
        """
    Create connecton to DB 
    Check if required table exist, if not then create tables params and values. 
    """

        self.engine = create_engine(db_connector, echo=False, connect_args={"check_same_thread": False})
        metadata = MetaData(bind=self.engine, reflect=True)

        if not self.engine.dialect.has_table(self.engine, 'params'):  # If table don't exist, Create.
            params_table = Table('params', metadata,
                                 Column('id', Integer, primary_key=True),
                                 Column('name', String),
                                 )
            metadata.create_all(self.engine)

        if not self.engine.dialect.has_table(self.engine, 'values'):  # If table don't exist, Create.
            values_table = Table('values', metadata,
                                 Column('id', Integer, primary_key=True),
                                 Column('param_id', Integer, ForeignKey('params.id')),
                                 Column('value', Float),
                                 Column('timestamp', DateTime(timezone=True), default=func.now()),
                                 )
            metadata.create_all(self.engine)

        orm.Mapper(Values, metadata.tables['values'])
        orm.Mapper(Params, metadata.tables['params'])
        self.session = orm.Session(bind=self.engine)

    def write_value(self, parametr_name, value):
        """
    Write value to values tables with parameter name
    """
        # check if  params exist if not then create
        q = self.session.query(Params).filter(Params.name == parametr_name)
        record = q.all()
        if len(record) == 0:
            param = Params(parametr_name)
            self.session.add(param)
            self.session.commit()
        # get  params id
        q = self.session.query(Params).filter(Params.name == parametr_name)
        record = q.all()
        params_id = record[0].id
        # write to db
        val = Values(params_id, value, datetime.now())
        self.session.add(val)
        self.session.commit()
        # self.session.close()

    def read_value(self, parametr_id, from_date, to_date):

        q = self.session.query(Values) \
            .filter(Values.param_id == parametr_id) \
            .filter(Values.timestamp <= to_date) \
            .filter(Values.timestamp >= from_date)

        return q.all()

    def take_params(self):
        q = self.session.query(Params)
        return q.all()

    def get_parameter_name(self, id):
        q = self.session.query(Params).filter(Params.id == id)
        record = q.one()
        return record.name


def main():
    logger = Db_log(DB_CONNECT)

    while True:
        cpu = psutil.cpu_percent(interval=5)
        memory = psutil.virtual_memory()
        try:
            logger.write_value('CPU', cpu)
            logger.write_value('Memory', memory.percent)
            logger.write_value('Memory in use', round(memory.used / (1024 * 1024)))
        except Exception as e:
            print(e)
        logger.session.close()


if __name__ == '__main__':
    main()
