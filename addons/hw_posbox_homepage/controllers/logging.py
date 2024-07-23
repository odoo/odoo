
import functools
import logging
import platform
import re

from .main import jinja_env

from odoo import http, tools
from odoo.addons.hw_drivers.tools import helpers
from odoo.addons.hw_drivers.server_logger import check_and_update_odoo_config_log_to_server_option, get_odoo_config_log_to_server_option
from odoo.http import request

LOGGING_HTML = jinja_env.get_template('logging.jinja2')
LOGGING_TABLE_HTML = jinja_env.get_template('logging_table.jinja2')

LOGGING_TABLE_PRIORITY = ('odoo', 'werkzeug', 'websocket')
LOGGING_TABLE_WHITELIST = {'root', r'odoo\.addons', r'odoo\.addons\.hw_drivers', r'odoo\.addons\.hw_drivers\..*', *LOGGING_TABLE_PRIORITY}

class LoggerNode:
    def __init__(self, logger_name:str, logger: logging.Logger) -> None:
        self.logger_name = logger_name
        self.logger = logger
        self.children = []
        self.parent = None

    @property
    def is_level_parent(self):
        return self.logger.getEffectiveLevel() == logging.NOTSET

    @property
    def level_str(self):
        return logging.getLevelName(self.logger.level).lower()

    @property
    def is_level_inherited(self):
        return self.logger.level == logging.NOTSET

    @property
    def level_efficient_str(self):
        return logging.getLevelName(self.logger.getEffectiveLevel()).lower()

    @property
    @functools.lru_cache()
    def exists(self):
        # Non-existing loggers will be `logging.PlaceHolder` instances
        return isinstance(self.logger, logging.Logger)

    @property
    @functools.lru_cache()
    def logger__name__(self):
        i = self.logger_name.rfind('.', 0, len(self.logger_name) - 1)
        if i == -1:
            return self.logger_name
        return self.logger_name[i + 1:]
    
    @property
    @functools.lru_cache()
    def available_levels(self):
        ret = ['debug', 'info', 'warning', 'error']
        if self.logger_name != 'root':
            ret = ['parent'] + ret
        return ret

    def add_child(self, child: 'LoggerNode', parent: 'LoggerNode'=None):
        child.parent = parent
        self.children.append(child)

def _save_odoo_config_file(should_save=True):
    if not should_save:
        return
    with helpers.writable():
        tools.config.save()

class IoTTechnicalLogging(http.Controller):
    @http.route('/technical/logging', type='http', auth='none', csrf=False)
    def logging(self, **post):
        if request.httprequest.method == 'POST':
            new_should_send_logs_to_server = post.get('log-to-server') == 'on' # we use .get() as if the HTML checkbox is unchecked, no value is given in the POST request

            _save_odoo_config_file(
                check_and_update_odoo_config_log_to_server_option(
                    new_should_send_logs_to_server
                )
            )

        return jinja_env.get_template('logging.jinja2').render({
            'os': platform.system(),
            'ip': helpers.get_ip(),
            'is_log_to_server_activated': get_odoo_config_log_to_server_option(),
        })

    @classmethod
    def _update_logger_level(cls, logger_name, new_level):
        # Checks
        assert new_level in {'debug', 'info', 'warning', 'error', 'parent'}, f"Invalid level '{new_level}'"
        assert cls._is_authorised_logger(logger_name), f"Logger '{logger_name}' is not authorised to modify"
        if logger_name == 'root':
            logger_name = ''  # change it as previosuly use this name for root logger
        assert logger_name == '' or logger_name in logging.Logger.manager.loggerDict, f"Logger '{logger_name}' does not exist"
        is_new_level_parent = new_level == 'parent'
        if logger_name == '':
            assert not is_new_level_parent, "Cannot set root logger to parent level"
        real_new_level = logging.NOTSET if is_new_level_parent else new_level.upper()

        # Change the level of the logger dynamically first
        logging.getLogger(logger_name).setLevel(real_new_level)


        # Edit odoo config file to persist the changes
        # `tools.config[ODOO_CONFIG_NAME_LOG_HANDLER]` value is a list of `<logger.name>:<LEVEL>`
        # e.g:[':INFO', 'werkzeug:CRITICAL', 'odoo.fields:WARNING']`

        # 1) Have a version of all loggers, without the modified one
        log_handlers_without_logger = [
            log_handler for log_handler in tools.config['log_handler'] if not log_handler.startswith(logger_name+':')
        ]
        # 2) Add the modified logger to the list. If it is parent level, then it will simply not be in the list
        if not is_new_level_parent:
            log_handlers_without_logger.append(f'{logger_name}:{real_new_level}')
        tools.config['log_handler'] = log_handlers_without_logger
        _save_odoo_config_file()

    @staticmethod
    def _is_authorised_logger(logger_name):
        return any(re.fullmatch(pattern, logger_name) for pattern in LOGGING_TABLE_WHITELIST)

    @http.route('/technical/logging/logging-table', type='http', auth='none', csrf=False)
    def logging_table(self, **logger_name_new_level_dict):
        if request.httprequest.method == 'POST':
            self._update_logger_level(*logger_name_new_level_dict.popitem())
        return jinja_env.get_template('logging_table.jinja2').render(log_tree=self._get_logger_tree())

    def _get_logger_tree(self):
        loggers = list(logging.Logger.manager.loggerDict.items())
        # apply whitelist
        loggers = [(name, logger) for name, logger in loggers if self._is_authorised_logger(name)]
        # sort by priority
        loggers = sorted(loggers, key=lambda x: (not x[0].startswith(LOGGING_TABLE_PRIORITY), x[0]))

        root = LoggerNode('root', logging.root)
        all_nodes = {}
        for logger_name, logger in loggers:
            all_nodes[logger_name] = node = LoggerNode(logger_name, logger)
            i = logger_name.rfind('.', 0, len(logger_name) - 1)  # same formula used in `logging`
            if i == -1:
                parent = root
            else:
                parent = all_nodes[logger_name[:i]]
            parent.add_child(node, parent)
        return root
