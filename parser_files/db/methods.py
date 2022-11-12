import os
import sys

from sqlalchemy.exc import IntegrityError
from sqlalchemy import create_engine, update
from sqlalchemy.orm import sessionmaker

import yaml


class MethodsMySQL:
    def __init__(self):
        engine = create_engine(self.read_yaml()[0]['mysql_path'],
                               echo=True, pool_size=10, pool_recycle=60, pool_pre_ping=True)
        Session = sessionmaker(bind=engine)
        Session.configure(bind=engine)
        self.session = Session()

    def read_yaml(self):
        with open(os.path.abspath(os.path.join(sys.argv[0], '../..', 'config.yaml'))) as fh:
            return yaml.safe_load(fh)

    def insert(self, dict_insert, class_table):
        ins = class_table(**dict_insert)
        self.session.add(ins)

        try:
            self.session.commit()
            self.session.close()
        except IntegrityError:
            self.update(dict_insert, class_table)

    def update(self, dict_insert, class_table):
        self.session.rollback()
        self.session.execute(
            update(class_table)
            .where(class_table.ws_id == dict_insert.get('ws_id'))
            .values(**dict_insert)
        )
        self.session.commit()
        self.session.close()
