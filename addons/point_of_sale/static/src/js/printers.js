/* global html2canvas */
odoo.define('point_of_sale.Printer', function (require) {
"use strict";

var Session = require('web.Session');
var core = require('web.core');
const { Gui } = require('point_of_sale.Gui');
var _t = core._t;

// IMPROVEMENT: This is too much. We can get away from this class.
class PrintResult {
    constructor({ successful, message }) {
        this.successful = successful;
        this.message = message;
    }
}

class PrintResultGenerator {
    IoTActionError() {
        return new PrintResult({
            successful: false,
            message: {
                title: _t('Connection to IoT Box failed'),
                body: _t('Please check if the IoT Box is still connected.'),
            },
        });
    }
    IoTResultError() {
        return new PrintResult({
            successful: false,
            message: {
                title: _t('Connection to the printer failed'),
                body: _t('Please check if the printer is still connected. \n' +
                    'Some browsers don\'t allow HTTP calls from websites to devices in the network (for security reasons). ' +
                    'If it is the case, you will need to follow Odoo\'s documentation for ' +
                    '\'Self-signed certificate for ePOS printers\' and \'Secure connection (HTTPS)\' to solve the issue'
                ),
            },
        });
    }
    Successful() {
        return new PrintResult({
            successful: true,
        });
    }
}

var PrinterMixin = {
    init: function (pos) {
        this.receipt_queue = [];
        this.printResultGenerator = new PrintResultGenerator();
        this.pos = pos;
    },

    /**
     * Add the receipt to the queue of receipts to be printed and process it.
     * We clear the print queue if printing is not successful.
     * @param {String} receipt: The receipt to be printed, in HTML
     * @returns {PrintResult}
     */
    print_receipt: async function(receipt) {
        if (receipt) {
            this.receipt_queue.push(receipt);
        }
        let image, sendPrintResult;
        while (this.receipt_queue.length > 0) {
            receipt = this.receipt_queue.shift();
            image = await this.htmlToImg(receipt);
            try {
                sendPrintResult = await this.send_printing_job(image);
            } catch (_error) {
                // Error in communicating to the IoT box.
                this.receipt_queue.length = 0;
                return this.printResultGenerator.IoTActionError();
            }
            // rpc call is okay but printing failed because
            // IoT box can't find a printer.
            if (!sendPrintResult || sendPrintResult.result === false) {
                this.receipt_queue.length = 0;
                return this.printResultGenerator.IoTResultError();
            }
        }
        return this.printResultGenerator.Successful();
    },

    /**
     * Generate a jpeg image from a canvas
     * @param {DOMElement} canvas
     */
    process_canvas: function (canvas) {
        return canvas.toDataURL('image/jpeg').replace('data:image/jpeg;base64,','');
    },

    /**
     * Renders the html as an image to print it
     * @param {String} receipt: The receipt to be printed, in HTML
     */
    htmlToImg: function (receipt) {
        $('.pos-receipt-print').html(receipt);
        this.receipt = $('.pos-receipt-print>.pos-receipt');
        // Odoo RTL support automatically flip left into right but html2canvas
        // won't work as expected if the receipt is aligned to the right of the
        // screen so we need to flip it back.
        this.receipt.parent().css({ left: 0, right: 'auto' });
        return html2canvas(this.receipt[0], {
            height: Math.ceil(this.receipt.outerHeight() + this.receipt.offset().top),
            width: Math.ceil(this.receipt.outerWidth() + 2 * this.receipt.offset().left),
            scale: 1,
        }).then(canvas => {
            $('.pos-receipt-print').empty();
            return this.process_canvas(canvas);
        });
    },

    _onIoTActionResult: function (data){
        if (this.pos && (data === false || data.result === false)) {
            Gui.showPopup('ErrorPopup',{
                'title': _t('Connection to the printer failed'),
                'body':  _t('Please check if the printer is still connected.'),
            });
        }
    },

    _onIoTActionFail: function () {
        if (this.pos) {
            Gui.showPopup('ErrorPopup',{
                'title': _t('Connection to IoT Box failed'),
                'body':  _t('Please check if the IoT Box is still connected.'),
            });
        }
    },
}

var Printer = core.Class.extend(PrinterMixin, {
    init: function (url, pos) {
        PrinterMixin.init.call(this, pos);
        this.connection = new Session(undefined, url || 'http://localhost:8069', { use_cors: true});
    },

    /**
     * Sends a command to the connected proxy to open the cashbox
     * (the physical box where you store the cash). Updates the status of
     * the printer with the answer from the proxy.
     */
    open_cashbox: function () {
        var self = this;
        return this.connection.rpc('/hw_proxy/default_printer_action', {
            data: {
                action: 'cashbox'
            }
        }).then(self._onIoTActionResult.bind(self))
            .guardedCatch(self._onIoTActionFail.bind(self));
    },

    /**
     * Sends the printing command the connected proxy
     * @param {String} img : The receipt to be printed, as an image
     */
    send_printing_job: function (img) {
        return this.connection.rpc('/hw_proxy/default_printer_action', {
            data: {
                action: 'print_receipt',
                receipt: img,
            }
        });
    },
});

return {
    PrinterMixin: PrinterMixin,
    Printer: Printer,
    PrintResult,
    PrintResultGenerator,
}
});
