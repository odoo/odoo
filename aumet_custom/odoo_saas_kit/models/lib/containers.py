import docker
import logging
import time
_logger = logging.getLogger(__name__)
from odoo.exceptions import UserError, Warning, ValidationError


class container(object):

    def __init__(self):
        self.dclient = None

    def get_client(self,host = "localhost"):
        try:
            if host == "localhost":
                self.dclient = docker.from_env()
            else:
                self.dclient = docker.DockerClient(base_url='tcp://%s:2375'%host)
        except Exception as e:
            _logger.info("Not able to get a docker client!!")
            return False
        return True

    def get_container(self,id):
        try:
            return self.dclient.containers.get(id)
        except docker.errors.NotFound as error:
            _logger.info("Error while getting container %r"%error)
            return False

def start_container(id,host = None):
    dock = container()
    dock.get_client(host = host)
    cont = dock.get_container(id)
    if not cont:
        _logger.info("Container couldnot be connected.")
        return False
    cont.restart()
    return True

def action(operation = None,container_id = None, host_server = None, db_server = None):
    if not container_id:
        raise UserError("Container id is required!")
    server_type = host_server['server_type']
    dock = container()
    isitlocal = True
    if server_type != "self":
        isitlocal = False

    dock.get_client(host = "localhost" if isitlocal else host_server['host'])
    cont = dock.get_container(container_id)
    if not cont:
        return False
    dispatch = {
        'start': cont.start,
        'stop': cont.stop,
        'restart': cont.restart,
        }
    if operation == 'restart':
        return start_container(container_id, host = "localhost" if isitlocal else host_server['host'])
    try:
        dispatch[operation]()
    except docker.errors.APIError as error:
        _logger.info("Error while perfoming %r operaton %r"%(operation,error))
        return False
    return True
