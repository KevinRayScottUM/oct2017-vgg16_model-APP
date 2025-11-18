import sqlite3

from flask import session


class Database:
    def __init__(self):
        self.conn = sqlite3.connect('flask-layui.sqlite')
        self.cursor = self.conn.cursor()

    def create_table(self):
        sql_statements = [
            """
            create table user
            (
                id       integer primary key,
                nickname varchar(255),
                mobile   varchar(255),
                password varchar(255),
                result varchar(255)
            );
            """,
            """
            create table CNV_DOC
            (
                id       integer primary key,
                nickname varchar(255),
                mobile   varchar(255),
                password_cnv varchar(255),
                result varchar(255)
            );
            """,
            """
            create table DME_DOC
            (
                id       integer primary key,
                nickname varchar(255),
                mobile   varchar(255),
                password_dme varchar(255),
                result varchar(255)
            );
            """,
            """
            create table DRUSEN_DOC
            (
                id       integer primary key,
                nickname varchar(255),
                mobile   varchar(255),
                password_drusen varchar(255),
                result varchar(255)
            );
            """
        ]

        for statement in sql_statements:
            self.cursor.execute(statement)
        self.conn.commit()

    def insert(self, nickname, mobile, password, result):
        sql = 'insert into user(nickname, mobile, password, result) values (?, ?, ?, ?);'
        self.cursor.execute(sql, (nickname, mobile, password, result))
        self.conn.commit()

    def search_info(self, mobile):
        sql = 'select nickname, result, mobile from user where mobile=?;'
        self.cursor.execute(sql, (mobile,))
        result = self.cursor.fetchone()
        print("查询结果:", result)  # 添加打印语句
        return result

    def search(self, mobile):
        sql = 'select password from user where mobile=?;'
        self.cursor.execute(sql, (mobile,))
        return self.cursor.fetchone()

    def search1(self, mobile):
        sql = 'select nickname, password from user where mobile=?;'
        self.cursor.execute(sql, (mobile,))
        result = self.cursor.fetchone()
        print("查询结果:", result)  # 添加打印语句
        return result

    def update_password(self, mobile, new_password):
        sql = 'update user set password=? where mobile=?;'
        self.cursor.execute(sql, (new_password, mobile))
        self.conn.commit()

    def insert_result(self, result):
        # 获取当前登录用户的手机号
        mobile = session.get('mobile')

        if mobile:
            # 更新当前登录用户的结果字段
            sql = 'UPDATE user SET result=? WHERE mobile=?;'
            self.cursor.execute(sql, (result, mobile))
            self.conn.commit()
        else:
            # 如果找不到当前登录用户，则打印错误信息
            print("未找到当前登录用户的手机号.")

db = Database()

if __name__ == '__main__':
    db.create_table()
    # db.insert('正心全栈编程', '18675867241', '123456')
    # ret = db.search('18675867241')
    # print(ret)