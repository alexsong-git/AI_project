import psycopg2
from psycopg2 import OperationalError, IntegrityError

database = 'ecm_saas'
user = 'postgres'
password = ''
db_host = 'seel-dev.cluster-c4pawlij3cb6.us-east-2.rds.amazonaws.com'
db_port = '5432'

def create_connection(db_name, db_user, db_password, db_host, db_port):
    """创建数据库连接"""
    connection = None
    try:
        connection = psycopg2.connect(
            database=db_name,
            user=db_user,
            password=db_password,
            host=db_host,
            port=db_port,
        )
        print("数据库连接成功")
    except OperationalError as e:
        print(f"连接错误: {e}")
    return connection


def execute_query(connection, query, params=None):
    """执行SQL查询（CREATE, INSERT, UPDATE, DELETE）"""
    cursor = connection.cursor()
    try:
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        connection.commit()
        print("查询执行成功")
    except IntegrityError as e:
        print(f"数据完整性错误: {e}")
        connection.rollback()
    except OperationalError as e:
        print(f"查询错误: {e}")
        connection.rollback()


def execute_read_query(connection, query, params=None):
    """执行查询并返回结果（SELECT）"""
    cursor = connection.cursor()
    result = None
    try:
        if params:
            cursor.execute(query, params)
        else:
            result = cursor.fetchall()
            return result
    except OperationalError as e:
        print(f"查询错误: {e}")
    return result


if __name__ == "__main__":
    # 数据库连接参数
    db_params = {
        "db_name": "your_database",
        "db_user": "your_username",
        "db_password": "your_password",
        "db_host": "localhost",
        "db_port": "5432"
    }

    # 创建连接
    conn = create_connection(**db_params)

    if conn:
        try:
            # 创建示例表
            create_table_query = """
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                age INT
            );
            """
            execute_query(conn, create_table_query)

            # 插入示例数据
            insert_user_query = """
            INSERT INTO users (name, email, age)
            VALUES (%s, %s, %s);
            """
            user_data = ("John Doe", "john@example.com", 30)
            execute_query(conn, insert_user_query, user_data)

            # 查询数据
            select_users_query = "SELECT * FROM users;"
            users = execute_read_query(conn, select_users_query)

            if users:
                print("\n用户列表:")
                for user in users:
                    print(user)

        finally:
            # 关闭连接
            if conn:
                conn.close()
                print("\n数据库连接已关闭")
