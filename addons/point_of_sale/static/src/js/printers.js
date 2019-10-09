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
        $('.pos-receipt-print').html(receipt);
        var promise = new Promise(function (resolve, reject) {
            self.receipt = $('.pos-receipt-print>.pos-receipt');
            html2canvas(self.receipt[0], {
                onparsed: function(queue) {
                    queue.stack.ctx.height = Math.ceil(self.receipt.outerHeight() + self.receipt.offset().top);
                },
                onrendered: function (canvas) {
                    $('.pos-receipt-print').empty();
                    resolve(self.process_canvas(canvas));
                } 
            })
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
