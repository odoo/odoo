import psycopg2
import sys
import logging
_logger = logging.getLogger(__name__)

class PgQuery(object):
    """
    USAGE:
    postgresX = ['localhost', 'sadsadsad', 'admin', 'webkul']
    pgX = TaskMigration(*postgresX)
    with pgX:
        result = pgX.selectQuery(query)
    """

    def __init__(self, host, database, user, password, port):
        self.host = host
        self.database = database
        self.user = user
        self.password = password
        self.dbConnection = False
        self.cursor = False
        self.port = port

    def __enter__(self):
        try:
            self.dbConnection = psycopg2.connect(host=self.host, database=self.database, user=self.user, password=self.password,port=self.port)
            self.cursor = self.dbConnection.cursor()
        except Exception as e:
            _logger.info("Error in Postgres Connection: %r"%e)
            sys.exit()
        return self.dbConnection

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.dbConnection:
            #self.dbConnection.close()
            pass

    def selectQuery(self, queryString):
        status = True
        try:
            self.cursor.execute(queryString)
        except Exception as e:
            print(queryString)
            print(e)
            status = False
            return status
        else:
            return self.cursor.fetchall()

    def executeQuery(self, queryString):
        status = True
        try:
            self.cursor.execute(queryString)
            self.dbConnection.commit()
        except Exception as e:
            _logger.info(queryString)
            _logger.info(e)
            status = False
        finally:
            return status