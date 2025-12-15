# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ctypes
import datetime
import logging
from abc import abstractmethod, ABC
from queue import Queue
from time import sleep


from odoo.addons.iot_drivers.driver import Driver
from odoo.addons.iot_drivers.event_manager import event_manager
from odoo.addons.iot_drivers.tools.system import IS_WINDOWS
from odoo.tools.misc import file_path

_logger = logging.getLogger(__name__)

# Buffer size big enough to hold every string incoming from ctypes libraries
# The biggest strings stored in this buffer are the receipts
CTYPES_BUFFER_SIZE = 10000

# Define pointers and argument types for ctypes function calls
ulong_pointer = ctypes.POINTER(ctypes.c_ulong)
double_pointer = ctypes.POINTER(ctypes.c_double)

# (Worldline specific) All the terminal errors can be found in the section "Codes d'erreur" here:
# https://help.winbooks.be/space/HelpLogFr/1278150/Liaison+vers+le+terminal+de+paiement+Banksys+en+TCP%2FIP#Codes-d'erreur
WORLDLINE_ERRORS = {
    '1802': 'Terminal is busy',
    '1803': 'Timeout expired',
    '1811': 'Technical problem',
    '1822': 'Connection failure',
    '2000': 'Unknown acquirer identifier',
    '2100': 'Action code not supported',
    '2625': 'Corrupted message',
    '2629': 'User cancellation',
    '2631': 'Host cancellation',
    '2632': 'Host error',
    '2633': 'Operation already performed',
    '2634': 'Operation busy',
    '2635': 'Operation not performed',
    '2800': 'Doesn’t exist',
    '2802': 'Not allowed',
    '2806': 'Bad signature',
    '2807': 'Conditional field missing',
    '2808': 'Not found',
    '2809': 'Dependency not found',
    '2810': 'Bad value',
    '2811': 'Bad sequence',
    '2812': 'Device attachment',
    '2813': 'Unexpected field',
    '3100': 'Chip card expected',
    '3101': 'Card not well read',
    '3102': 'Condition of use not satisfied',
    '4000': 'Purse technical problem',
    '4001': 'Purse host identifier invalid',
    '4002': 'Purse SDA certificate error',
    '4003': 'Purse extended SDA certificate error',
    '4004': 'Purse in red list',
    '4005': 'Purse is locked for credit',
    '4006': 'Purse is locked for debit',
    '4007': 'Purse expired',
    '4008': 'Purse state error',
    '4009': 'Purse recovery error',
    '4010': 'Purse key identifier error',
    '4011': 'Purse balance too large',
    '4012': 'Insufficient purse balance',
    '4100': 'No purse in reader and time out expired',
    '4101': 'Time-out on fallback card reading',
    '4102': 'Problem linked to card',
    '4103': 'Card information not available',
    '4200': 'Entered amount invalid',
    '4201': 'Double operation',
    '4202': 'Invalid currency',
    '4203': 'Amount higher than authorized amount',
    '4204': 'Floor limit exceeded in EMV mode',
    '4205': 'Transaction refused by the terminal in EMV mode',
    '4206': 'Transaction refused by the card in EMV mode',
    '4207': 'Product not available',
    '4300': 'Service (already) activated',
    '4301': 'Service (already) deactivated',
    '4302': 'Maximal transaction number per (calendar) month reached',
    '4303': 'Maximal uncollected journals number reached',
    '4304': 'Service activation not supported',
    '4305': 'Maximum transaction records reached',
    '4306': 'Maximum service activation number reached',
    '6003': 'Paper jam',
    '6004': 'Remove previous ticket',
    '6005': 'No paper',
    '6006': 'Low paper',
    '6008': 'Printer specific',
    '7806': 'Product not allowed',
    '7808': 'Bad pump number',
    '7816': 'Incorrect pump session number',
    '7817': 'Transaction amount null',
    '7818': 'Transaction amount null and quantity null',
    '7819': 'Pump unhooked time-out expiration',
    '9002': 'No key fault',
    '9003': 'Cryptographic fault',
    '9004': 'No PIN fault',
    '9005': 'Bad MAC',
    '9006': 'Bad MDC',
}

# (Worldline specific) Manually cancelled by cashier, do not show these errors
IGNORE_WORLDLINE_ERRORS = [
    '2628',  # External Equipment Cancellation
    '2630',  # Device Cancellation
]


def import_ctypes_library(lib_subfolder: str, lib_name: str):
    """Import a library using ctypes, independently of the OS.

    e.g.: library is located under ``iot_drivers/iot_handlers/drivers/ctep/libeasyctep.so``, then
    ``lib_subfolder="ctep"`` and ``lib_name="libeasyctep.so"``

    :param lib_subfolder: The subfolder where the library is located under
    ``iot_drivers/iot_handlers/drivers/``
    :param lib_name: The name of the library file. Must respect the OS
    extension (.so/.dll), otherwise ValueError will be raised
    :return: The imported ctypes library object, or None if import failed
    """
    supported_lib_extensions = '.dll' if IS_WINDOWS else '.so'
    import_library_method = ctypes.WinDLL if IS_WINDOWS else ctypes.CDLL

    try:
        lib_path = file_path(f'iot_drivers/iot_handlers/drivers/{lib_subfolder}/{lib_name}', supported_lib_extensions)
        ctypes_lib = import_library_method(lib_path)
        _logger.info('Successfully imported ctypes library "%s" from %s', lib_name, lib_path)
        return ctypes_lib
    except (OSError, ValueError, FileNotFoundError):
        _logger.exception(
            "Failed to import ctypes library '%s' from iot_drivers/iot_handlers/drivers/%s/",
            lib_name, lib_subfolder
        )


def create_ctypes_string_buffer():
    """Create a ctypes buffer of CTYPES_BUFFER_SIZE size"""
    return ctypes.create_string_buffer(CTYPES_BUFFER_SIZE)


class CtypesTerminalDriver(Driver, ABC):
    """
    This class is the parent class of all the terminal drivers using ctypes.
    Worldline and Six drivers are inheriting from this class.
    """

    DELAY_TIME_BETWEEN_TRANSACTIONS = 5  # seconds

    def __init__(self, identifier, device, lib_name: str, manufacturer: str):
        super().__init__(identifier, device)
        self.device_type = 'payment'
        self.device_connection = 'network'
        self.cid = None
        self.owner = None
        self.queue_actions = Queue()
        self.terminal_busy = False

        self._actions[''] = self._action_default
        self.next_transaction_min_dt = datetime.datetime.min

        self.device_manufacturer = manufacturer
        self.device_name = f"{self.device_manufacturer} terminal {self.device_identifier}"
        self.terminal = import_ctypes_library(self.connection_type, lib_name)

    @classmethod
    def supported(cls, device):
        # Currently all devices detected through TimInterface or CTEPInterface are supported
        return True

    def _action_default(self, data):
        data_message_type = data.get('messageType')
        _logger.debug('%s: _action_default %s %s', self.device_name, data_message_type, data)
        if data_message_type in ['Transaction', 'Balance']:
            if self.terminal_busy:
                self.send_status(error=f'{self.device_name} is currently busy. Try again later.', request_data=data)
            else:
                self.terminal_busy = True
                self.queue_actions.put(data)
        elif data_message_type == 'Cancel':
            self.cancel_transaction(data)

    def run(self):
        while True:
            # If the queue is empty, the call of "get" will block and wait for it to get an item
            action = self.queue_actions.get()
            action_type = action.get('messageType')
            _logger.debug("%s: Starting next action in queue: %s", self.device_name, action_type)
            if action_type == 'Transaction':
                self.process_transaction(action)
            elif action_type == 'Balance':
                self.six_terminal_balance(action)  # Only for Worldline "Six" (TIM)
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

    def send_status(self, value='', response=False, stage=False, ticket=False, ticket_merchant=False, card=False, card_no=False, transaction_id=False, error=False, disconnected=False, request_data=False):
        self.data['status'] = 'success'  # always success: let service handle errors
        self.data['result'] = {
            'value': value,
            'Stage': stage,
            'Response': response,
            'Ticket': ticket,
            'TicketMerchant': ticket_merchant,
            'Card': card,
            'CardNo': card_no,
            'PaymentTransactionID': transaction_id,
            'Error': error,
            'Disconnected': disconnected,
            'cid': request_data.get('cid'),
        }
        # TODO: add `stacklevel=2` in image with python version > 3.8
        _logger.debug('%s: send_status data: %s', self.device_name, self.data, stack_info=True)
        event_manager.device_changed(self, request_data)

    def process_transaction(self, transaction: dict):
        """This method should be overridden by child classes to implement the
        transaction processing logic.

        Child methods can use super().process_transaction(transaction) to call this base method
        for common pre-processing steps.

        :param transaction: transaction details.
        """
        if transaction['amount'] <= 0:
            self.send_status(
                error='The terminal cannot process negative or null transactions.',
                request_data=transaction
            )
            return False

        self._check_transaction_delay()  # Force wait before starting transaction if necessary
        self.send_status(stage='WaitingForCard', request_data=transaction)
        return True

    @abstractmethod
    def cancel_transaction(self, transaction):
        """
        Method implementing the ongoing transaction request cancellation
        """

    def six_terminal_balance(self, transaction):
        """
        Method implementing the terminal balance request (only for Worldline "Six")
        Not an abstract method as it remains undefined for Worldline
        """
