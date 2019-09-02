
odoo.define('pos_epson_printer.Printer', function (require) {
"use strict";

var core = require('web.core');
var PrinterMixin = require('point_of_sale.Printer').PrinterMixin;

var _t = core._t;

var EpsonPrinter = core.Class.extend(PrinterMixin, {
    init: function (ip, pos) {
        PrinterMixin.init.call(this, arguments);
        this.pos = pos;
        this.ePOSDevice = new epson.ePOSDevice();
        var port = window.location.protocol === 'http:' ? '8008' : '8043';
        this.ePOSDevice.connect(ip, port, this.callback_connect.bind(this), {eposprint: true});
    },

    callback_connect: function (resultConnect) {
        var self = this;
        var deviceId = 'local_printer';
        var options = {'crypto' : false, 'buffer' : false};
        if ((resultConnect == 'OK') || (resultConnect == 'SSL_CONNECT_OK')) {
            this.ePOSDevice.createDevice(deviceId, this.ePOSDevice.DEVICE_TYPE_PRINTER, options, this.callback_createDevice.bind(this));
        } else {
            this.pos.chrome.ready.then(function () {
                self.pos.gui.show_popup('error', {
                    'title': _t('Connection to the printer failed'),
                    'body':  _t('Please check if the printer is still connected, if the configured IP address is correct and if your printer supports the ePOS protocol.'),
                });
            });
        }
    },

    callback_createDevice: function (deviceObj, errorCode) {
        var self = this;
        if (deviceObj === null) {
            this.pos.gui.show_popup('error', {
                'title': _t('Connection to the printer failed'),
                'body':  _t('Please check if the printer is still connected. Error code: ') + errorCode,
            });
            return;
        }
        this.printer = deviceObj;
        this.printer.onreceive = function(response){
            if (!response.success) {
                self.pos.gui.show_popup('error', {
                    'title': _t('Epson ePOS Error'),
                    'body':  _t('An error happened while sending data to the printer. Error code: ') + response.code,
                });
            }
        };
    },

    /**
     * Create the print request for webPRNT from a canvas
     * 
     * @override
     */
    process_canvas: function (canvas) {
        if (this.printer) {
            this.printer.addTextAlign(this.printer.ALIGN_CENTER);
            this.printer.addImage(canvas.getContext('2d'), 0, 0, canvas.width, canvas.height);
            this.printer.addCut();
        }
    },

    /**
     * @override
     */
    open_cashbox: function () {
        if (this.printer) {
            this.printer.addPulse();
            this.printer.send();
        }
    },

    /**
     * @override
     */
    send_printing_job: function () {
        if (this.printer) {
            this.printer.send();
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Not applicable to Epson ePOS
     * @override
     */
    _onIoTActionFail: function () {},
    _onIoTActionResult: function () {},
});

return EpsonPrinter;

});
