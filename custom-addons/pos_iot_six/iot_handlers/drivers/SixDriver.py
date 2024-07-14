# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from platform import system
import ctypes
from time import sleep
from logging import getLogger

from odoo.addons.hw_drivers.iot_handlers.lib.ctypes_terminal_driver import CtypesTerminalDriver, import_ctypes_library, CTYPES_BUFFER_SIZE, create_ctypes_string_buffer


_logger = getLogger(__name__)
CANCELLED_BY_POS = 2 # Error code returned when you press "cancel" in PoS

# Load library
LIB_NAME = 'libsix_odoo_w.dll' if system() == 'Windows' else 'libsix_odoo_l.so'
TIMAPI = import_ctypes_library('tim', LIB_NAME)

# int six_cancel_transaction(t_terminal_manager *terminal_manager)
TIMAPI.six_cancel_transaction.argtypes = [ctypes.c_void_p]

# int six_perform_transaction
TIMAPI.six_perform_transaction.argtypes = [
    ctypes.c_void_p,                # t_terminal_manager *terminal_manager
    ctypes.c_char_p,                # char *pos_id
    ctypes.c_int,                   # int user_id

    ctypes.c_int,                   # int transaction_type
    ctypes.c_int,                   # int amount
    ctypes.c_char_p,                # char *currency_str

    ctypes.c_char_p,                # char *transaction_id,
    ctypes.c_int,                   # int transaction_id_size
    ctypes.c_char_p,                # char *merchant_receipt
    ctypes.c_char_p,                # char *customer_receipt
    ctypes.c_int,                   # int receipt_size
    ctypes.c_char_p,                # char *card
    ctypes.c_int,                   # int card_size
    ctypes.POINTER(ctypes.c_int),   # int *error_code
    ctypes.c_char_p,                # char *error
    ctypes.c_int,                   # int error_size
]

class SixDriver(CtypesTerminalDriver):
    connection_type = 'tim'

    def __init__(self, identifier, device):
        super(SixDriver, self).__init__(identifier, device)
        self.device_name = 'Six terminal %s' % self.device_identifier
        self.device_manufacturer = 'Six'

    def processTransaction(self, transaction):
        if transaction['amount'] <= 0:
            return self.send_status(error='The terminal cannot process null transactions.', request_data=transaction)

        # Notify PoS about the transaction start
        self.send_status(stage='WaitingForCard', request_data=transaction)

        # Transaction buffers
        ctypes_int_buffer_size = ctypes.c_int(CTYPES_BUFFER_SIZE)
        transaction_id = create_ctypes_string_buffer()
        merchant_receipt = create_ctypes_string_buffer()
        customer_receipt = create_ctypes_string_buffer()
        card = create_ctypes_string_buffer()
        error_code = ctypes.c_int(CTYPES_BUFFER_SIZE)
        error = create_ctypes_string_buffer()

        # Transaction
        try:
            result = TIMAPI.six_perform_transaction(
                ctypes.cast(self.dev, ctypes.c_void_p),  # t_terminal_manager *terminal_manager
                transaction['posId'].encode(),  # char *pos_id
                ctypes.c_int(transaction['userId']),  # int user_id
                ctypes.c_int(1) if transaction['transactionType'] == 'Payment' else ctypes.c_int(2),  # int transaction_type
                ctypes.c_int(transaction['amount']),  # int amount
                transaction['currency'].encode(),  # char *currency_str
                transaction_id,  # char *transaction_id
                ctypes_int_buffer_size,  # int transaction_id_size
                merchant_receipt,  # char *merchant_receipt
                customer_receipt,  # char *customer_receipt
                ctypes_int_buffer_size,   # int receipt_size
                card,  # char *card
                ctypes_int_buffer_size,  # int card_size
                ctypes.byref(error_code),  # int *error_code
                error,  # char *error
                ctypes_int_buffer_size  # int error_size
            )
            # Transaction successful
            if result == 1:
                self.send_status(
                    response='Approved',
                    ticket=customer_receipt.value,
                    ticket_merchant=merchant_receipt.value,
                    card=card.value,
                    transaction_id=transaction_id.value,
                    request_data=transaction,
                )
            # Transaction failed
            elif result == 0:
                # If cancelled by Odoo Pos
                if error_code.value == CANCELLED_BY_POS:
                    sleep(3)  # Wait a couple of seconds between cancel requests as per documentation
                    self.send_status(stage='Cancel', request_data=transaction)
                # If an error was encountered
                else:
                    error_message = f"{error_code.value}: {error.value.decode()}"
                    self.send_status(error=error_message, request_data=transaction)
            # Terminal disconnected
            elif result == -1:
                self.send_status(disconnected=True)
        except OSError:
            _logger.exception("Failed to perform Six transaction. Check for potential segmentation faults")
            sleep(3)  # needed to space out transaction requests
            self.send_status(
                error="An error has occured. Check the transaction result manually with the payment provider",
                request_data=transaction,
            )

    def cancelTransaction(self, transaction):
        self.send_status(stage='waitingCancel', request_data=transaction)
        try:
            if not TIMAPI.six_cancel_transaction(ctypes.cast(self.dev, ctypes.c_void_p)):
                self.send_status(stage='Cancel', error='Transaction could not be cancelled', request_data=transaction)
        except OSError:
            _logger.exception("Failed to cancel Six transaction. Check for potential segmentation faults.")
            sleep(3)  # needed to space out cancellation requests
            self.send_status(
                error="An error has occured when cancelling Six transaction. Check the transaction result manually with the payment provider",
                request_data=transaction,
            )
