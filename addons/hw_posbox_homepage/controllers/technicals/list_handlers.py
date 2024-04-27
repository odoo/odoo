
from pathlib import Path

import logging


from odoo import http, tools
from odoo.http import request
from odoo.addons.hw_drivers.tools import helpers
from odoo.addons.hw_drivers.server_logger import check_and_update_odoo_config_log_to_server_option, get_odoo_config_log_to_server_option
from odoo.addons.hw_posbox_homepage.controllers.jinja import render_template
from odoo.tools.misc import file_path

_logger = logging.getLogger(__name__)


class IoTTechnicalListHandlersPage(http.Controller):
    @http.route('/list_handlers', type='http', auth='none', website=True, csrf=False, save_session=False)
    def list_handlers(self, **post):
        AVAILABLE_LOG_LEVELS = ('debug', 'info', 'warning', 'error')
        if request.httprequest.method == 'POST':
            need_config_save = False  # If the config file needed to be saved at the end

            # Check and update "send logs to server"
            need_config_save |= check_and_update_odoo_config_log_to_server_option(
                post.get('log-to-server') == 'on'  # we use .get() as if the HTML checkbox is unchecked, no value is given in the POST request
            )

            # Check and update logging levels
            IOT_LOGGING_PREFIX = 'iot-logging-'
            INTERFACE_PREFIX = 'interface-'
            DRIVER_PREFIX = 'driver-'
            AVAILABLE_LOG_LEVELS_WITH_PARENT = AVAILABLE_LOG_LEVELS + ('parent',)
            for post_request_key, log_level_or_parent in post.items():
                if not post_request_key.startswith(IOT_LOGGING_PREFIX):
                    # probably a new post request payload argument not related to logging
                    continue
                post_request_key = post_request_key[len(IOT_LOGGING_PREFIX):]

                if post_request_key == 'root':
                    need_config_save |= self._update_logger_level('', log_level_or_parent, AVAILABLE_LOG_LEVELS)
                elif post_request_key == 'odoo':
                    need_config_save |= self._update_logger_level('odoo', log_level_or_parent, AVAILABLE_LOG_LEVELS)
                    need_config_save |= self._update_logger_level('werkzeug', log_level_or_parent if log_level_or_parent != 'debug' else 'info', AVAILABLE_LOG_LEVELS)
                elif post_request_key.startswith(INTERFACE_PREFIX):
                    logger_name = post_request_key[len(INTERFACE_PREFIX):]
                    need_config_save |= self._update_logger_level(logger_name, log_level_or_parent, AVAILABLE_LOG_LEVELS_WITH_PARENT, 'interfaces')
                elif post_request_key.startswith(DRIVER_PREFIX):
                    logger_name = post_request_key[len(DRIVER_PREFIX):]
                    need_config_save |= self._update_logger_level(logger_name, log_level_or_parent, AVAILABLE_LOG_LEVELS_WITH_PARENT, 'drivers')
                else:
                    _logger.warning('Unhandled iot logger: %s', post_request_key)

            # Update and save the config file (in case of IoT box reset)
            if need_config_save:
                with helpers.writable():
                    tools.config.save()
        drivers_list = helpers.list_file_by_os(file_path('hw_drivers/iot_handlers/drivers'))
        interfaces_list = helpers.list_file_by_os(file_path('hw_drivers/iot_handlers/interfaces'))
        return render_template('technical/list_handlers.jinja2',
            drivers_list=drivers_list,
            interfaces_list=interfaces_list,
            server=helpers.get_odoo_server_url(),
            is_log_to_server_activated=get_odoo_config_log_to_server_option(),
            root_logger_log_level=self._get_logger_effective_level_str(logging.getLogger()),
            odoo_current_log_level=self._get_logger_effective_level_str(logging.getLogger('odoo')),
            recommended_log_level='warning',
            available_log_levels=AVAILABLE_LOG_LEVELS,
            drivers_logger_info=self._get_iot_handlers_logger(drivers_list, 'drivers'),
            interfaces_logger_info=self._get_iot_handlers_logger(interfaces_list, 'interfaces'),
        )

    @http.route('/load_iot_handlers', type='http', auth='none', website=True)
    def load_iot_handlers(self):
        helpers.download_iot_handlers(False)
        helpers.odoo_restart(0)
        return "<meta http-equiv='refresh' content='20; url=http://" + helpers.get_ip() + ":8069/list_handlers'>"

    @http.route('/handlers_clear', type='http', auth='none', cors='*', csrf=False)
    def clear_handlers_list(self):
        for directory in ['drivers', 'interfaces']:
            for file in list(Path(file_path(f'hw_drivers/iot_handlers/{directory}')).glob('*')):
                if file.name != '__pycache__':
                    helpers.unlink_file(str(file.relative_to(*file.parts[:3])))
        return "<meta http-equiv='refresh' content='0; url=http://" + helpers.get_ip() + ":8069/list_handlers'>"

    def _get_logger_effective_level_str(self, logger):
        return logging.getLevelName(logger.getEffectiveLevel()).lower()

    def _get_iot_handler_logger(self, handler_name, handler_folder_name):
        """
        Get Odoo Iot logger given an IoT handler name
        :param handler_name: name of the IoT handler
        :param handler_folder_name: IoT handler folder name (interfaces or drivers)
        :return: logger if any, False otherwise
        """
        odoo_addon_handler_path = helpers.compute_iot_handlers_addon_name(handler_folder_name, handler_name)
        return odoo_addon_handler_path in logging.Logger.manager.loggerDict and \
               logging.getLogger(odoo_addon_handler_path)

    def _update_logger_level(self, logger_name, new_level, available_log_levels, handler_folder=False):
        """
        Update (if necessary) Odoo's configuration and logger to the given logger_name to the given level.
        The responsibility of saving the config file is not managed here.
        :param logger_name: name of the logging logger to change level
        :param new_level: new log level to set for this logger
        :param available_log_levels: iterable of logs levels allowed (for initial check)
        :param handler_folder: optional string of the IoT handler folder name ('interfaces' or 'drivers')
        :return: wherever some changes were performed or not on the config
        """
        if new_level not in available_log_levels:
            _logger.warning('Unknown level to set on logger %s: %s', logger_name, new_level)
            return False

        if handler_folder:
            logger = self._get_iot_handler_logger(logger_name, handler_folder)
            if not logger:
                _logger.warning('Unable to change log level for logger %s as logger missing', logger_name)
                return False
            logger_name = logger.name

        ODOO_TOOL_CONFIG_HANDLER_NAME = 'log_handler'
        LOG_HANDLERS = tools.config[ODOO_TOOL_CONFIG_HANDLER_NAME]
        LOGGER_PREFIX = logger_name + ':'
        IS_NEW_LEVEL_PARENT = new_level == 'parent'

        if not IS_NEW_LEVEL_PARENT:
            intended_to_find = LOGGER_PREFIX + new_level.upper()
            if intended_to_find in LOG_HANDLERS:
                # There is nothing to do, the entry is already inside
                return False

        # We remove every occurrence for the given logger
        log_handlers_without_logger = [
            log_handler for log_handler in LOG_HANDLERS if not log_handler.startswith(LOGGER_PREFIX)
        ]

        if IS_NEW_LEVEL_PARENT:
            # We must check that there is no existing entries using this logger (whatever the level)
            if len(log_handlers_without_logger) == len(LOG_HANDLERS):
                return False

        # We add if necessary new logger entry
        # If it is "parent" it means we want it to inherit from the parent logger.
        # In order to do this we have to make sure that no entries for the logger exists in the
        # `log_handler` (which is the case at this point as long as we don't re-add an entry)
        tools.config[ODOO_TOOL_CONFIG_HANDLER_NAME] = log_handlers_without_logger
        new_level_upper_case = new_level.upper()
        if not IS_NEW_LEVEL_PARENT:
            new_entry = [LOGGER_PREFIX + new_level_upper_case]
            tools.config[ODOO_TOOL_CONFIG_HANDLER_NAME] += new_entry
            _logger.debug('Adding to odoo config log_handler: %s', new_entry)

        # Update the logger dynamically
        real_new_level = logging.NOTSET if IS_NEW_LEVEL_PARENT else new_level_upper_case
        _logger.debug('Change logger %s level to %s', logger_name, real_new_level)
        logging.getLogger(logger_name).setLevel(real_new_level)
        return True

    def _get_iot_handlers_logger(self, handlers_name, iot_handler_folder_name):
        """
        :param handlers_name: List of IoT handler string to search the loggers of
        :param iot_handler_folder_name: name of the handler folder ('interfaces' or 'drivers')
        :return:
        {
            <iot_handler_name_1> : {
                'level': <logger_level_1>,
                'is_using_parent_level': <logger_use_parent_level_or_not_1>,
                'parent_name': <logger_parent_name_1>,
            },
            ...
        }
        """
        handlers_loggers_level = dict()
        for handler_name in handlers_name:
            handler_logger = self._get_iot_handler_logger(handler_name, iot_handler_folder_name)
            if not handler_logger:
                # Might happen if the file didn't define a logger (or not init yet)
                handlers_loggers_level[handler_name] = False
                _logger.debug('Unable to find logger for handler %s', handler_name)
                continue
            logger_parent = handler_logger.parent
            handlers_loggers_level[handler_name] = {
                'level': self._get_logger_effective_level_str(handler_logger),
                'is_using_parent_level': handler_logger.level == logging.NOTSET,
                'parent_name': logger_parent.name,
                'parent_level': self._get_logger_effective_level_str(logger_parent),
            }
        return handlers_loggers_level
