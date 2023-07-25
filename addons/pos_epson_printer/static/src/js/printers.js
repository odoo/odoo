
odoo.define('pos_epson_printer.Printer', function (require) {
"use strict";

var core = require('web.core');
var { PrinterMixin, PrintResult, PrintResultGenerator } = require('point_of_sale.Printer');

var QWeb = core.qweb;
var _t = core._t;

class EpsonPrintResultGenerator extends PrintResultGenerator {
    constructor(address) {
        super();
        this.address = address;
    }

    IoTActionError() {
        var printRes = new PrintResult({
            successful: false,
            message: {
                title: _t('Connection to the printer failed'),
                body: _t('Please check if the printer is still connected. \n' +
                    'Some browsers don\'t allow HTTP calls from websites to devices in the network (for security reasons). ' +
                    'If it is the case, you will need to follow Odoo\'s documentation for ' +
                    '\'Self-signed certificate for ePOS printers\' and \'Secure connection (HTTPS)\' to solve the issue'
                ),
            }
        });

        if (window.location.protocol === 'https:') {
            printRes.message.body += _.str.sprintf(
                _t('If you are on a secure server (HTTPS) please make sure you manually accepted the certificate by accessing %s'),
                this.address
            );
        }

        return printRes;
    }

    IoTResultError(printerErrorCode) {
        let message = _t("The printer was successfully reached, but it wasn't able to print.") + '\n';
        if (printerErrorCode) {
            message += '\n' + _t("The following error code was given by the printer:") + '\n' + printerErrorCode;

            const extra_messages = {
                'DeviceNotFound':
                    _t("Check on the printer configuration for the 'Device ID' setting. " +
                        "It should be set to: ") + "\nlocal_printer",
                'EPTR_REC_EMPTY':
                    _t("No paper was detected by the printer"),
            };
            if (printerErrorCode in extra_messages) {
                message += '\n' + extra_messages[printerErrorCode];
            }
            message += "\n" + _t("To find more details on the error reason, please search online for:") + '\n' +
                " Epson Server Direct Print " + printerErrorCode;
        } else {
            message += _t('Please check if the printer has enough paper and is ready to print.');
        }
        return new PrintResult({
            successful: false,
            message: {
                title: _t('Printing failed'),
                body: message,
            },
        });
    }
}

var EpsonPrinter = core.Class.extend(PrinterMixin, {
    init(ip, pos) {
        PrinterMixin.init.call(this, pos);
        var url = window.location.protocol + '//' + ip;
        this.address = url + '/cgi-bin/epos/service.cgi?devid=local_printer';
        this.printResultGenerator = new EpsonPrintResultGenerator(url);
    },


    /**
     * Transform a (potentially colored) canvas into a monochrome raster image.
     * We will use Floyd-Steinberg dithering.
     */
    _canvasToRaster(canvas) {
        var imageData = canvas.getContext('2d').getImageData(0, 0, canvas.width, canvas.height);
        var pixels = imageData.data;
        var width = imageData.width;
        var height = imageData.height;
        var errors = Array.from(Array(width), _ => Array(height).fill(0));
        var rasterData = new Array(width * height).fill(0);

        for (var y = 0; y < height; y++) {
            for (var x = 0; x < width; x++) {
                var idx, oldColor, newColor;

                // Compute grayscale level. Those coefficients were found online
                // as R, G and B have different impacts on the darkness
                // perception (e.g. pure blue is darker than red or green).
                idx = (y * width + x) * 4;
                oldColor = pixels[idx] * 0.299 + pixels[idx+1] * 0.587 + pixels[idx+2] * 0.114;

                // Propagate the error from neighbor pixels 
                oldColor += errors[x][y];
                oldColor = Math.min(255, Math.max(0, oldColor));

                if (oldColor < 128) {
                    // This pixel should be black
                    newColor = 0;
                    rasterData[y * width + x] = 1;
                } else {
                    // This pixel should be white
                    newColor = 255;
                    rasterData[y * width + x] = 0;
                }

                // Propagate the error to the following pixels, based on
                // Floyd-Steinberg dithering.
                var error = oldColor - newColor;
                if (error) {
                    if (x < width - 1) {
                        // Pixel on the right
                        errors[x + 1][y] += 7/16 * error;
                    }
                    if (x > 0 && y < height - 1) {
                        // Pixel on the bottom left
                        errors[x - 1][y + 1] += 3/16 * error;
                    }
                    if (y < height - 1) {
                        // Pixel below
                        errors[x][y + 1] += 5/16 * error;
                    }
                    if (x < width - 1 && y < height - 1) {
                        // Pixel on the bottom right
                        errors[x + 1][y + 1] += 1/16 * error;
                    }
                }
            }
        }

        return rasterData.join('');
    },

    /**
     * Base 64 encode a raster image
     */
    _encodeRaster(rasterData) {
        var encodedData = '';
        for(var i = 0; i < rasterData.length; i+=8){
            var sub = rasterData.substr(i, 8);
            encodedData += String.fromCharCode(parseInt(sub, 2));
        }
        return btoa(encodedData);
    },

    /**
     * Create the raster data from a canvas
     * 
     * @override
     */
    process_canvas(canvas) {
        var rasterData = this._canvasToRaster(canvas);
        var encodedData = this._encodeRaster(rasterData);
        return QWeb.render('ePOSPrintImage', {
            image: encodedData,
            width: canvas.width,
            height: canvas.height,
        });
    },

    /**
     * @override
     */
    open_cashbox() {
        var pulse = QWeb.render('ePOSDrawer');
        this.send_printing_job(pulse);
    },

    /**
     * @override
     */
    async send_printing_job(img) {
        const res = await $.ajax({
            url: this.address,
            method: 'POST',
            data: img,
        });
        const response = $(res).find('response');
        return {"result": response.attr('success') === 'true', "printerErrorCode": response.attr('code')};
    },
});

return EpsonPrinter;

});
