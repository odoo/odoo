# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ctypes
import datetime
import logging

from odoo.addons.hw_drivers.iot_handlers.lib.ctypes_terminal_driver import CtypesTerminalDriver, ulong_pointer, double_pointer, import_ctypes_library, create_ctypes_string_buffer

_logger = logging.getLogger(__name__)

# All the terminal errors can be found in the section "Codes d'erreur" here:
# https://help.winbooks.be/pages/viewpage.action?pageId=64455643#LiaisonversleterminaldepaiementBanksysenTCP/IP-Codesd'erreur
TERMINAL_ERRORS = {
    '1802': 'Terminal is busy',
    '1803': 'Timeout expired',
    '2629': 'User cancellation',
    '2631': 'Host cancellation',
}

# Manually cancelled by cashier, do not show these errors
IGNORE_ERRORS = [
    '2628', # External Equipment Cancellation
    '2630', # Device Cancellation
]

easyCTEP = import_ctypes_library('ctep', 'libeasyctep.so')

# int startTransaction(
easyCTEP.startTransaction.argtypes = [
    ctypes.c_void_p,    # std::shared_ptr<ect::CTEPTerminal> trm
    ctypes.c_char_p,    # char const* amount
    ctypes.c_char_p,    # char const* reference
    ctypes.c_ulong,     # unsigned long action_identifier
    ctypes.c_char_p,    # char* merchant_receipt
    ctypes.c_char_p,    # char* customer_receipt
    ctypes.c_char_p,    # char* card
    ctypes.c_char_p     # char* error
]

# int abortTransaction(std::shared_ptr<ect::CTEPTerminal> trm, char* error)
easyCTEP.abortTransaction.argtypes = [ctypes.c_void_p, ctypes.c_char_p]

# int lastTransactionStatus(
easyCTEP.lastTransactionStatus.argtypes = [
    ctypes.c_void_p,    # std::shared_ptr<ect::CTEPTerminal> trm
    ulong_pointer,      # unsigned long* action_identifier
    double_pointer,     # double* amount
    ctypes.c_char_p,    # char* time,
    ctypes.c_char_p     # char* error
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
        result = easyCTEP.startTransaction(
            ctypes.byref(self.dev), # std::shared_ptr<ect::CTEPTerminal> trm
            ctypes.c_char_p(str(transaction_amount).encode('utf-8')),  # char const* amount
            ctypes.c_char_p(str(transaction_id).encode('utf-8')), # char const* reference
            ctypes.c_ulong(transaction_action_identifier),    # unsigned long action_identifier
            merchant_receipt,   # char* merchant_receipt
            customer_receipt, # char* customer_receipt
            card,   # char* card
            error_code, # char* error
        )
        _logger.debug('finished transaction #%d with result %d', transaction_id, result)

        self.next_transaction_min_dt = datetime.datetime.now() + datetime.timedelta(seconds=self.DELAY_TIME_BETWEEN_TRANSACTIONS)

        if result == 1:
            # Transaction successful
            self.send_status(
                response='Approved',
                ticket=customer_receipt.value,
                ticket_merchant=merchant_receipt.value,
                card=card.value,
                transaction_id=transaction['actionIdentifier'],
                request_data=transaction,
            )
        elif result == 0:
            error_code = error_code.value.decode('utf-8')
            # Transaction failed
            if error_code not in IGNORE_ERRORS:
                error_msg = '%s (Error code: %s)' % (TERMINAL_ERRORS.get(error_code, 'Transaction was not processed correctly'), error_code)
                logging.info(error_msg)
                self.send_status(error=error_msg, request_data=transaction)
            # Transaction was cancelled
            else:
                self.send_status(stage='Cancel', request_data=transaction)
        elif result == -1:
            # Terminal disconnection, check status manually
            self.send_status(disconnected=True, request_data=transaction)

    def cancelTransaction(self, transaction):
        # Force to wait before starting the transaction if necessary
        self._check_transaction_delay()
        self.send_status(stage='waitingCancel', request_data=transaction)

        error_code = create_ctypes_string_buffer()
        _logger.info("cancel transaction request")
        result = easyCTEP.abortTransaction(ctypes.byref(self.dev), error_code) # std::shared_ptr<ect::CTEPTerminal> trm
        _logger.debug("end cancel transaction request")

        if not result:
            error_code = error_code.value.decode('utf-8')
            error_msg = '%s (Error code: %s)' % (TERMINAL_ERRORS.get(error_code, 'Transaction could not be cancelled'), error_code)
            _logger.info(error_msg)
            self.send_status(stage='Cancel', error=error_msg, request_data=transaction)

    def lastTransactionStatus(self, request_data):
        action_identifier = ctypes.c_ulong()
        amount = ctypes.c_double()
        time = create_ctypes_string_buffer()
        error_code = create_ctypes_string_buffer()
        _logger.info("last transaction status request")
        result = easyCTEP.lastTransactionStatus(ctypes.byref(self.dev), ctypes.byref(action_identifier), ctypes.byref(amount), time, error_code)
        _logger.debug("end last transaction status request")

        if result:
            self.send_status(
                value={
                    'action_identifier': action_identifier.value,
                    'amount': amount.value,
                    'time': time.value,
                },
                request_data=request_data,
            )
        else:
            error_code = error_code.value.decode('utf-8')
            error_msg = '%s (Error code: %s)' % (TERMINAL_ERRORS.get(error_code, 'Last Transaction was not processed correctly'), error_code)
            self.send_status(
                value={
                    'error' : error_msg,
                },
                request_data=request_data,
            )
