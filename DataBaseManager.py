import sqlalchemy as db
from sqlalchemy.dialects.postgresql import insert

from aiogram.types import User

from datetime import datetime

from typing import Union


class UsersTable:
    _instance = None

    def __new__(cls, connection, engine):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, connection: db.Connection, engine: db.Engine) -> None:
        self._connection = connection
        meta_data = db.MetaData()
        self._table: db.Table = db.Table(
            'users',
            meta_data,
            db.Column('id', db.Integer, primary_key=True),
            db.Column('fullname', db.VARCHAR(100)),
            db.Column('username', db.VARCHAR(50)),
            db.Column('created_at', db.TIMESTAMP),
            db.Column('language', db.VARCHAR(5))
        )
        meta_data.create_all(engine)

    def insert(self, user: User, created_at: datetime = datetime.now()) -> Union[bool, Exception]:
        try:
            insertion_query = insert(self._table).values(
                {
                    'id': user.id,
                    'fullname': user.full_name,
                    'username': user.username,
                    'created_at': created_at,
                    'language': user.language_code,
                }
            )
            on_conflict_query = insertion_query.on_conflict_do_update(
                index_elements=['id'],
                set_={
                    'fullname': user.full_name,
                    'username': user.username,
                    'language': user.language_code,
                }
            )
            self._connection.execute(on_conflict_query)
            self._connection.commit()
            return True
        except Exception as ex:
            return ex

    def delete_by_id(self, user_id: int):
        delete_query = self._table.delete().where(
            self._table.columns.user_id == user_id
        )
        self._connection.execute(delete_query)
        self._connection.commit()

    def select_all(self) -> db.CursorResult:
        select_all_query = db.select(self._table)
        select_all_result = self._connection.execute(select_all_query)
        return select_all_result

    @property
    def table(self) -> db.Table:
        return self._table


class PromptsTable:
    _instance = None

    def __new__(cls, connection, engine, users):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, connection: db.Connection, engine: db.Engine, users: db.Table) -> None:
        self._connection = connection
        meta_data = db.MetaData()
        self._table: db.Table = db.Table(
            'prompts',
            meta_data,
            db.Column('id', db.Integer, primary_key=True, autoincrement=True),
            db.Column('user_id', db.ForeignKey(users.columns.id)),
            db.Column('prompt', db.VARCHAR(100)),
            db.Column('status', db.Enum("job", "queue", "done", name='status_enum', create_type=False)),
            db.Column('created_at', db.TIMESTAMP),
            db.Column('message_id', db.INT),
        )
        meta_data.create_all(engine)

    def insert(self, user_id: int, prompt: str, status: str, message_id: int,
               created_at: datetime = datetime.now()) -> Union[int, Exception]:
        try:
            if status not in ('job', 'queue', 'done'):
                raise ValueError("Invalid status value")
            insertion_query = insert(self._table).values(
                {
                    'user_id': user_id,
                    'prompt': prompt,
                    'status': status,
                    'message_id': message_id,
                    'created_at': created_at,
                }
            )

            result = self._connection.execute(insertion_query)
            self._connection.commit()

            return result.inserted_primary_key[0]
        except Exception as ex:
            return ex

    def update(self, prompt_id: int, status: str) -> Union[int, Exception]:
        try:
            if status not in ('job', 'queue', 'done'):
                raise ValueError("Invalid status value")
            update_query = self._table.update().where(self._table.c.id == prompt_id).values(status=status)

            self._connection.execute(update_query)
            self._connection.commit()

            return prompt_id
        except Exception as ex:
            return ex

    def get_records(self):
        try:
            select_query = self._table.select()\
                .where(self._table.c.status.in_(["job", "queue"]))\
                .order_by(self._table.c.created_at)

            result = self._connection.execute(select_query)
            records = result.fetchall()

            return records

        except Exception as ex:
            return ex

    def get_records_by_user_id(self, user_id: int):
        try:
            select_query = self._table.select().where(self._table.c.user_id == user_id)\
                .order_by(self._table.c.created_at.desc())
            result = self._connection.execute(select_query)
            records = result.fetchall()

            return records

        except Exception as ex:
            return ex

    def select_all(self) -> db.CursorResult:
        select_all_query = db.select(self._table)
        select_all_result = self._connection.execute(select_all_query)
        return select_all_result

    def delete_by_id(self, prompt_id: int, user_id: int):
        try:
            # Check if the record with the given id and user_id exists before attempting deletion
            exists_query = self._table.select().where(
                (self._table.columns.id == prompt_id) & (self._table.columns.user_id == user_id)
            )
            result = self._connection.execute(exists_query)

            if not result.fetchone():
                return False

            delete_query = self._table.delete().where(
                (self._table.columns.id == prompt_id) & (self._table.columns.user_id == user_id)
            )
            self._connection.execute(delete_query)
            self._connection.commit()
            return True

        except Exception:
            return False

    @property
    def table(self) -> db.Table:
        return self._table


class DataBaseManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        self._engine: db.Engine = db.create_engine(
            'postgresql+psycopg2://aiogram_user:aiogram_password@postgres/aiogram_db')
        self._connection: db.Connection = self._engine.connect()
        self._metadata: db.MetaData = db.MetaData()
        self.users: UsersTable = UsersTable(connection=self._connection, engine=self._engine)
        self.prompts: PromptsTable = PromptsTable(connection=self._connection, engine=self._engine,
                                                  users=self.users.table)

    @property
    def connection(self) -> db.Connection:
        return self._connection

    @property
    def metadata(self) -> db.MetaData:
        return self._metadata

    def execute(self, to_execute: db.Executable):
        self.connection.execute(to_execute)
        self._connection.commit()


def create_db() -> DataBaseManager:
    return DataBaseManager()
