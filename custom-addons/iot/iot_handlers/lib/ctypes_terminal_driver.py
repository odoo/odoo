# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ctypes
import datetime
import logging
from abc import abstractmethod
from platform import system
from queue import Queue
from time import sleep


from odoo.addons.hw_drivers.driver import Driver
from odoo.addons.hw_drivers.event_manager import event_manager
from odoo.tools.misc import file_path

_logger = logging.getLogger(__name__)

# Buffer size big enough to hold every string incoming from ctypes libraries
# The biggest strings stored in this buffer are the receipts
CTYPES_BUFFER_SIZE = 1000

# Define pointers and argument types for ctypes function calls
ulong_pointer = ctypes.POINTER(ctypes.c_ulong)
double_pointer = ctypes.POINTER(ctypes.c_double)

def import_ctypes_library(lib_subfolder, lib_name):
    """
    Import a library using ctypes, independently of the OS.
    :param lib_subfolder: The subfolder where the library is located under "hw_drivers/iot_handlers/lib"
    :param lib_name: The name of the library file. Must respect the OS extension (.so/.dll), otherwise ValueError will be raised
    Example: if the library is located under "hw_drivers/iot_handlers/lib/ctep/libeasyctep.so", then
    lib_subfolder = "ctep" and lib_name = "libeasyctep.so"
    """
    if system() == 'Windows':
        supported_lib_extensions = '.dll'
        import_library_method = ctypes.WinDLL
    else:
        supported_lib_extensions = '.so'
        import_library_method = ctypes.CDLL

    try:
        lib_path = file_path(f'hw_drivers/iot_handlers/lib/{lib_subfolder}/{lib_name}', supported_lib_extensions)
        ctypes_lib = import_library_method(lib_path)
        _logger.info('Successfully imported ctypes library "%s" from %s', lib_name, lib_path)
        return ctypes_lib
    except (OSError, ValueError, FileNotFoundError):
        _logger.exception('Failed to import ctypes library "%s" from hw_drivers/iot_handlers/lib/%s/', lib_name, lib_subfolder)

def create_ctypes_string_buffer():
    """
    Create a ctypes buffer of CTYPES_BUFFER_SIZE size
    """
    return ctypes.create_string_buffer(CTYPES_BUFFER_SIZE)

class CtypesTerminalDriver(Driver):
    """
    This class is the parent class of all the terminal drivers using ctypes.
    Worldline and Six drivers are inheriting from this class.
    """

    DELAY_TIME_BETWEEN_TRANSACTIONS = 5  # seconds

    def __init__(self, identifier, device):
        super().__init__(identifier, device)
        self.device_type = 'payment'
        self.device_connection = 'network'
        self.cid = None
        self.owner = None
        self.queue_actions = Queue()
        self.terminal_busy = False

        self._actions[''] = self._action_default
        self.next_transaction_min_dt = datetime.datetime.min

    @classmethod
    def supported(cls, device):
        # Currently all devices detected through TimInterface or CTEPInterface are supported
        return True

    def _action_default(self, data):
        data_message_type = data.get('messageType')
        data['owner'] = self.data.get('owner')
        _logger.debug('%s: _action_default %s %s', self.device_name, data_message_type, data)
        if data_message_type in ['Transaction', 'LastTransactionStatus']:
            if self.terminal_busy:
                self.send_status(error=f'{self.device_name} is currently busy. Try again later.', request_data=data)
            else:
                self.terminal_busy = True
                self.queue_actions.put(data)
        elif data_message_type == 'Cancel':
            self.cancelTransaction(data)

    def run(self):
        while True:
            # If the queue is empty, the call of "get" will block and wait for it to get an item
            action = self.queue_actions.get()
            action_type = action.get('messageType')
            _logger.debug("%s: Starting next action in queue: %s", self.device_name, action_type)
            if action_type == 'Transaction':
                self.processTransaction(action)
            elif action_type == 'LastTransactionStatus':
                self.lastTransactionStatus(action)  # Only for Worldline
            self.terminal_busy = False

    def _check_transaction_delay(self):
        # After a payment has been processed, the display on the terminal still shows some
        # information for about 4-5 seconds. No request can be processed during this period.
        delay_diff = (self.next_transaction_min_dt - datetime.datetime.now()).total_seconds()
        if delay_diff > 0:
            if delay_diff > self.DELAY_TIME_BETWEEN_TRANSACTIONS:
                # Theoretically not possible, but to avoid sleeping for ages, we cap the value
                _logger.warning('%s: Transaction delay difference is too high %.2f force set as default', self.device_name, delay_diff)
                delay_diff = self.DELAY_TIME_BETWEEN_TRANSACTIONS
            _logger.info('%s: Previous transaction is too recent, will sleep for %.2f seconds', self.device_name, delay_diff)
            sleep(delay_diff)

    def send_status(self, value='', response=False, stage=False, ticket=False, ticket_merchant=False, card=False, transaction_id=False, error=False, disconnected=False, request_data=False):
        self.data = {
            'value': value,
            'Stage': stage,
            'Response': response,
            'Ticket': ticket,
            'TicketMerchant': ticket_merchant,
            'Card': card,
            'PaymentTransactionID': transaction_id,
            'Error': error,
            'Disconnected': disconnected,
            'owner': request_data.get('owner'),
            'cid': request_data.get('cid'),
        }
        # TODO: add `stacklevel=2` in image with python version > 3.8
        _logger.debug('%s: send_status data: %s', self.device_name, self.data, stack_info=True)
        event_manager.device_changed(self)

    # The following methods need to be implemented by the children classes
    @abstractmethod
    def processTransaction(self, transaction):
        """
        Method implementing the transaction processing
        """

    @abstractmethod
    def cancelTransaction(self, transaction):
        """
        Method implementing the ongoing transaction request cancellation
        """

    def lastTransactionStatus(self, transaction):
        """
        Method implementing the last transaction status request (only for Worldline)
        Not an abstract method as it remains undefined for Six
        """
