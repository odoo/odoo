# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ctypes
import datetime
import logging

from odoo.addons.hw_drivers.iot_handlers.lib.ctypes_terminal_driver import CtypesTerminalDriver, ulong_pointer, double_pointer, import_ctypes_library, create_ctypes_string_buffer

_logger = logging.getLogger(__name__)

# Load library
easyCTEP = import_ctypes_library('ctep_w', 'libeasyctep.dll')

# int startTransaction(
easyCTEP.startTransaction.argtypes = [
    ctypes.c_void_p, # CTEPManager* manager
    ctypes.c_char_p, # char const* amount
    ctypes.c_char_p, # char const* reference
    ctypes.c_ulong,  # unsigned long action_identifier
    ctypes.c_char_p, # char* merchant_receipt
    ctypes.c_char_p, # char* customer_receipt
    ctypes.c_char_p, # char* card
    ctypes.c_char_p  # char* error
]

# int abortTransaction(CTEPManager* manager, char* error)
easyCTEP.abortTransaction.argtypes = [ctypes.c_void_p, ctypes.c_char_p]

# All the terminal errors can be found in the section "Codes d'erreur" here:
# https://help.winbooks.be/space/HelpLogFr/1278150/Liaison+vers+le+terminal+de+paiement+Banksys+en+TCP%2FIP#Codes-d'erreur
TERMINAL_ERRORS = {
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

# Manually cancelled by cashier, do not show these errors
IGNORE_ERRORS = [
    '2628', # External Equipment Cancellation
    '2630', # Device Cancellation
]

class WorldlineDriver(CtypesTerminalDriver):
    connection_type = 'ctep'

    def __init__(self, identifier, device):
        super(WorldlineDriver, self).__init__(identifier, device)
        self.device_name = 'Worldline terminal %s' % self.device_identifier
        self.device_manufacturer = 'Worldline'

    def processTransaction(self, transaction):
        if transaction['amount'] <= 0:
            return self.send_status(error='The terminal cannot process negative or null transactions.', request_data=transaction)

        # Force to wait before starting the transaction if necessary
        self._check_transaction_delay()
        # Notify transaction start
        self.send_status(stage='WaitingForCard', request_data=transaction)

        # Transaction
        merchant_receipt = create_ctypes_string_buffer()
        customer_receipt = create_ctypes_string_buffer()
        card = create_ctypes_string_buffer()
        error_code = create_ctypes_string_buffer()
        transaction_id = transaction['TransactionID']
        transaction_amount = transaction['amount'] / 100
        transaction_action_identifier = transaction['actionIdentifier']
        _logger.info('start transaction #%d amount: %f action_identifier: %d', transaction_id, transaction_amount, transaction_action_identifier)

        try:
            result = easyCTEP.startTransaction(
                ctypes.cast(self.dev, ctypes.c_void_p),  # CTEPManager* manager
                ctypes.c_char_p(str(transaction_amount).encode('utf-8')),  # char const* amount
                ctypes.c_char_p(str(transaction_id).encode('utf-8')),  # char const* reference
                ctypes.c_ulong(transaction_action_identifier),  # unsigned long action_identifier
                merchant_receipt,  # char* merchant_receipt
                customer_receipt,  # char* customer_receipt
                card,  # char* card
                error_code,  # char* error
            )
            self.next_transaction_min_dt = datetime.datetime.now() + datetime.timedelta(seconds=self.DELAY_TIME_BETWEEN_TRANSACTIONS)

            if result == 1:
                # Transaction successful
                _logger.info('succesfully finished transaction #%d', transaction_id)
                self.send_status(
                    response='Approved',
                    ticket=customer_receipt.value,
                    ticket_merchant=merchant_receipt.value,
                    card=card.value,
                    transaction_id=transaction['actionIdentifier'],
                    request_data=transaction,
                )
            elif result == 0:
                # Transaction failed
                error_code = error_code.value.decode('utf-8')
                if error_code not in IGNORE_ERRORS:
                    error_msg = f'transaction #{transaction_id} error: {error_code}: {TERMINAL_ERRORS.get(error_code, "Transaction Error")}'
                    _logger.info(error_msg)
                    self.send_status(error=error_msg, request_data=transaction)
                # Transaction was cancelled
                else:
                    _logger.info("transaction #%d cancelled by PoS user", transaction_id)
                    self.send_status(stage='Cancel', request_data=transaction)
            elif result == -1:
                # Terminal disconnection, check status manually
                _logger.warning("terminal disconnected during transaction #%d", transaction_id)
                self.send_status(disconnected=True, request_data=transaction)

        except OSError:
            _logger.exception("Failed to perform Worldline transaction. Check for potential segmentation faults")
            self.send_status(
                error="An error has occured. Check the transaction result manually with the payment provider",
                request_data=transaction,
            )

    def cancelTransaction(self, transaction):
        # Force to wait before starting the transaction if necessary
        self._check_transaction_delay()
        self.send_status(stage='waitingCancel', request_data=transaction)

        error_code = create_ctypes_string_buffer()
        _logger.info("cancel transaction request")
        try:
            result = easyCTEP.abortTransaction(ctypes.cast(self.dev, ctypes.c_void_p), error_code)
            _logger.debug("end cancel transaction request")

            if not result:
                error_code = error_code.value.decode('utf-8')
                error_msg = '%s (Error code: %s)' % (TERMINAL_ERRORS.get(error_code, 'Transaction could not be cancelled'), error_code)
                _logger.info(error_msg)
                self.send_status(stage='Cancel', error=error_msg, request_data=transaction)
        except OSError:
            _logger.exception("Failed to cancel Worldline transaction. Check for potential segmentation faults.")
            self.send_status(
                stage='Cancel',
                error="An error has occured when cancelling Worldline transaction. Check the transaction result manually with the payment provider",
                request_data=transaction,
            )
