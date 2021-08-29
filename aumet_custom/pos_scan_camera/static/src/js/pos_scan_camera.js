odoo.define('pos_scan_camera', function (require) {
    "use strict";

    var chrome = require('point_of_sale.chrome');
    var core = require('web.core');
    var _t = core._t;
    var PosBaseWidget = require('point_of_sale.BaseWidget');


    var liveStreamConfig = {
        inputStream: {
            type: "LiveStream",
            constraints: {
                width: {min: 640},
                height: {min: 480},
                aspectRatio: {min: 1, max: 100},
                facingMode: "environment" // or "user" for the front camera
            }
        },
        locator: {
            patchSize: "medium",
            halfSample: true
        },
        numOfWorkers: (navigator.hardwareConcurrency ? navigator.hardwareConcurrency : 4),
        decoder: {
            "readers": [
                {"format": "ean_reader", "config": {}}
            ]
        },
        locate: true
    };
    var fileConfig = $.extend(
        {},
        liveStreamConfig,
        {
            inputStream: {
                size: 800
            }
        }
    );

    var CameraScanBarcodeWidget = PosBaseWidget.extend({
        template: 'CameraScanBarcodeWidget',
        init: function (parent, options) {
            var self = this;
            this._super(parent, options);
            this.state = 'connecting';
            this.pos.bind('change:camera_status', function (pos, status) {
                self.change_status_display(status['state']);
                self.state = status['state'];
            }, this);
        },

        change_status_display: function (status) {
            var msg = '';
            if (status === 'connected') {
                this.$('.js_warning').addClass('oe_hidden');
                this.$('.js_disconnected').addClass('oe_hidden');
                this.$('.js_connected').removeClass('oe_hidden');
            } else if (status === 'connecting') {
                this.$('.js_disconnected').addClass('oe_hidden');
                this.$('.js_connected').addClass('oe_hidden');
                this.$('.js_connecting').removeClass('oe_hidden');
                msg = _t('Connecting');
            } else {
                this.$('.js_warning').addClass('oe_hidden');
                this.$('.js_connected').addClass('oe_hidden');
                this.$('.js_disconnected').removeClass('oe_hidden');
                msg = _t('Camera Disconnected');
                if (status === 'not_found') {
                    msg = _t('Camera not found')
                }
            }

            this.$('.oe_customer_display_text').text(msg);
        },
        start: function () {
            this.show();
            var self = this;
            this.$el.click(function () {
                var body = '';
                if (self.state == 'connected') {
                    body = _t('Cammera ready scan any barcode');
                } else {
                    body = _t('Your Cammera turn off or Your Odoo domain not https (SSL)');
                }
                self.pos.gui.show_popup('confirm', {
                    title: _t('Status of Camera'),
                    body: body,
                })
                self.chrome.init_camera();
            });
        },
    });

    chrome.Chrome.include({
        init_camera: function () {
            var self = this;
            self.pos.gui.close_popup();
            try {
                Quagga.init(
                    liveStreamConfig,
                    function (err) {
                        if (err) {
                            $('.card-issue').html('<div class="alert alert-danger"><strong><i class="fa fa-exclamation-triangle"></i> ' + err.name + '</strong>: ' + err.message + '</div>');
                            Quagga.stop();
                            return;
                        }
                        Quagga.start();
                        self.pos.set('camera_status', {state: 'connected', pending: 1});
                    }
                );
            } catch (e) {
                console.warn(e);
                alert("Your Camera Device not ready scanning barode. This future only support SSL (https). Please setup your Odoo within ssl")
                self.pos.set('camera_status', {state: 'Disconnected', pending: 1});
            }
        },
        add_camera_scan_barcode_event: function () {
            if (this.camera_registered) {
                return
            }
            var self = this;
            Quagga.onProcessed(function (result) {
                var drawingCtx = Quagga.canvas.ctx.overlay,
                    drawingCanvas = Quagga.canvas.dom.overlay;

                if (result) {
                    if (result.boxes) {
                        drawingCtx.clearRect(0, 0, parseInt(drawingCanvas.getAttribute("width")), parseInt(drawingCanvas.getAttribute("height")));
                        result.boxes.filter(function (box) {
                            return box !== result.box;
                        }).forEach(function (box) {
                            Quagga.ImageDebug.drawPath(box, {x: 0, y: 1}, drawingCtx, {color: "green", lineWidth: 2});
                        });
                    }

                    if (result.box) {
                        Quagga.ImageDebug.drawPath(result.box, {x: 0, y: 1}, drawingCtx, {color: "#00F", lineWidth: 2});
                    }

                    if (result.codeResult && result.codeResult.code) {
                        Quagga.ImageDebug.drawPath(result.line, {x: 'x', y: 'y'}, drawingCtx, {
                            color: 'red',
                            lineWidth: 3
                        });
                    }
                }
            });

            // Once a barcode had been read successfully, stop quagga and
            // close the modal after a second to let the user notice where
            // the barcode had actually been found.
            Quagga.onDetected(function (result) {
                if (result.codeResult.code) {
                    self.pos.gui.close_popup();
                    var code = result.codeResult.code;
                    Quagga.stop();
                    self.pos.set('camera_status', {state: 'connected', pending: 1});
                    self.pos.barcode_reader.scan(code);
                    self.pos.gui.play_sound('bell');
                    setTimeout(function () {
                        self.init_camera();
                    }, self.pos.config.barcode_scan_timeout)
                }
            });
            this.camera_registered = true;
        },
        build_widgets: function () {

            if (this.pos.config.barcode_scan_with_camera) {
                this.pos.set('camera_status', {state: 'connecting', pending: 1});
                this.init_camera();
                this.add_camera_scan_barcode_event();
                this.widgets.push(
                    {
                        'name': 'CameraScanBarcodeWidget',
                        'widget': CameraScanBarcodeWidget,
                        'append': '.pos-rightheader',
                    }
                );
            }
            this._super();
        }
    });
});