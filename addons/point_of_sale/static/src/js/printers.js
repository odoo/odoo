odoo.define('point_of_sale.Printer', function (require) {
"use strict";

var Session = require('web.Session');
var core = require('web.core');
var _t = core._t;

var PrinterMixin = {
    init: function () {
        this.receipt_queue = [];
    },

    /**
     * Add the receipt to the queue of receipts to be printed and process it.
     * @param {String} receipt: The receipt to be printed, in HTML
     */
    print_receipt: function (receipt) {
        var self = this;
        if (receipt) {
            this.receipt_queue.push(receipt);
        }
        function process_next_job() {
            if (self.receipt_queue.length > 0) {
                var r = self.receipt_queue.shift();
                self.htmlToImg(r)
                    .then(self.send_printing_job.bind(self))
                    .then(self._onIoTActionResult.bind(self))
                    .then(process_next_job)
                    .guardedCatch(self._onIoTActionFail.bind(self));
            }
        }
        process_next_job();
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
        var self = this;
        $('.pos-receipts').html(receipt);
        $('.pos-receipt').addClass('pos-receipt-print');
        var promise = new Promise(function (resolve, reject) {
            html2canvas($('.pos-receipt')[0], {
                ignoreElements: function (node) {
                    // By default, html2canvas copies the whole DOM even if we just capture a part
                    // of it. When copying the list of products, it gets all of the product from the
                    // backend. We ignore the content of <div class="pos"> to speed things up.
                    if (node.className == "pos") {
                        return true;
                    }
                    return false;
                }
            }).then(function (canvas) {
                $('.pos-receipts').empty();
                resolve(self.process_canvas(canvas));
            });
        });
        return promise;
    },

    _onIoTActionResult: function (data){
        if (this.pos && (data === false || data.result === false)) {
            this.pos.gui.show_popup('error',{
                'title': _t('Connection to the printer failed'),
                'body':  _t('Please check if the printer is still connected.'),
            });
        }
    },

    _onIoTActionFail: function () {
        if (this.pos) {
            this.pos.gui.show_popup('error',{
                'title': _t('Connection to IoT Box failed'),
                'body':  _t('Please check if the IoT Box is still connected.'),
            });
        }
    },
}

var Printer = core.Class.extend(PrinterMixin, {
    init: function (url, pos) {
        PrinterMixin.init.call(this, arguments);
        this.pos = pos;
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
}
});
