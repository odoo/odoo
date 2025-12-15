# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ctypes
import datetime
import logging

from odoo.addons.iot_drivers.tools.system import IS_RPI
from odoo.addons.iot_drivers.iot_handlers.drivers.ctypes_terminal_driver import (
    CtypesTerminalDriver,
    create_ctypes_string_buffer,
    WORLDLINE_ERRORS,
    IGNORE_WORLDLINE_ERRORS,
)

_logger = logging.getLogger(__name__)


class WorldlineDriver(CtypesTerminalDriver):
    connection_type = 'ctep'

    def __init__(self, identifier, device):
        lib_name = "libeasyctep.so" if IS_RPI else "libeasyctep.dll"
        super().__init__(identifier, device, lib_name=lib_name, manufacturer="Worldline")

        # int startTransaction(
        self.terminal.startTransaction.argtypes = [
            ctypes.c_void_p,  # std::shared_ptr<ect::CTEPTerminal> trm if IS_RPI else CTEPManager* manager
            ctypes.c_char_p,  # char const* amount
            ctypes.c_char_p,  # char const* reference
            ctypes.c_ulong,  # unsigned long action_identifier
            ctypes.c_char_p,  # char* merchant_receipt
            ctypes.c_char_p,  # char* customer_receipt
            ctypes.c_char_p,  # char* card
            ctypes.c_char_p  # char* error
        ]

        # int abortTransaction(std::shared_ptr<ect::CTEPTerminal> trm if IS_RPI else CTEPManager* manager, char* error)
        self.terminal.abortTransaction.argtypes = [ctypes.c_void_p, ctypes.c_char_p]

    def process_transaction(self, transaction):
        if not super().process_transaction(transaction):
            return None

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
            device = ctypes.byref(self.dev) if IS_RPI else ctypes.cast(self.dev, ctypes.c_void_p)
            result = self.terminal.startTransaction(
                device,  # std::shared_ptr<ect::CTEPTerminal> trm if IS_RPI else CTEPManager* manager
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
                return self.send_status(
                    response='Approved',
                    ticket=customer_receipt.value.decode(),
                    ticket_merchant=merchant_receipt.value.decode(),
                    card=card.value.decode(),
                    transaction_id=transaction['actionIdentifier'],
                    request_data=transaction,
                )
            elif result == 0:
                # Transaction failed
                error_code = error_code.value.decode('utf-8')
                if error_code not in IGNORE_WORLDLINE_ERRORS:
                    error_msg = f'transaction #{transaction_id} error: {error_code}: {WORLDLINE_ERRORS.get(error_code, "Transaction Error")}'
                    _logger.info(error_msg)
                    return self.send_status(error=error_msg, request_data=transaction)
                # Transaction was cancelled
                else:
                    _logger.info("transaction #%d cancelled by PoS user", transaction_id)
                    return self.send_status(stage='Cancel', request_data=transaction)
            elif result == -1:
                # Terminal disconnection, check status manually
                _logger.warning("terminal disconnected during transaction #%d", transaction_id)
                return self.send_status(disconnected=True, request_data=transaction)

            return None
        except OSError:
            _logger.exception("Failed to perform Worldline transaction. Check for potential segmentation faults")
            return self.send_status(
                error="An error has occured. Check the transaction result manually with the payment provider",
                request_data=transaction,
            )

    def cancel_transaction(self, transaction):
        # Force to wait before starting the transaction if necessary
        self._check_transaction_delay()
        self.send_status(stage='waitingCancel', request_data=transaction)

        error_code = create_ctypes_string_buffer()
        _logger.info("cancel transaction request for: %s", transaction)
        try:
            device = ctypes.byref(self.dev) if IS_RPI else ctypes.cast(self.dev, ctypes.c_void_p)
            result = self.terminal.abortTransaction(device, error_code)
            _logger.debug("end cancel transaction request")

            if not result:
                error_code = error_code.value.decode('utf-8')
                error_msg = f"{WORLDLINE_ERRORS.get(error_code, 'Transaction could not be cancelled')}: {error_code}"
                _logger.info(error_msg)
                self.send_status(stage='Cancel', error=error_msg, request_data=transaction)
        except OSError:
            _logger.exception("Failed to cancel Worldline transaction. Check for potential segmentation faults.")
            self.send_status(
                stage='Cancel',
                error="An error has occured when cancelling Worldline transaction. Check the transaction result manually with the payment provider",
                request_data=transaction,
            )
