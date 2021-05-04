odoo.define('pos_mercury.PointOfSaleModel', function (require) {
    'use strict';

    const PointOfSaleModel = require('point_of_sale.PointOfSaleModel');
    const { patch } = require('web.utils');

    patch(PointOfSaleModel.prototype, 'pos_mercury', {
        _getPaymentInfo(payment) {
            const result = this._super(payment);
            result.mercury_data = payment._extras.mercury_data;
            result.mercury_auth_code = payment._extras.mercury_auth_code;
            return result;
        },
        getPaymentJSON(payment) {
            const result = this._super(payment);
            if (this.isMercuryPayment(payment)) {
                Object.assign(result, {
                    mercury_card_number: payment.mercury_card_number,
                    mercury_card_brand: payment.mercury_card_brand,
                    mercury_card_owner_name: payment.mercury_card_owner_name,
                    mercury_ref_no: payment.mercury_ref_no,
                    mercury_record_no: payment.mercury_record_no,
                    mercury_invoice_no: payment.mercury_invoice_no,
                    mercury_auth_code: payment._extras.mercury_auth_code,
                    mercury_data: payment._extras.mercury_data,
                });
            }
            return result;
        },
        getMercuryPaymentName(payment) {
            if (payment.mercury_card_number) {
                return payment.mercury_card_brand + ' (****' + payment.mercury_card_number + ')';
            } else {
                return '';
            }
        },
        getMercuryPaymentMethods() {
            return this.data.derived.paymentMethods.filter((paymentMethod) => {
                return paymentMethod.pos_mercury_config_id;
            });
        },
        decodeMagtek: function (magtekInput) {
            // Regular expression to identify and extract data from the track 1 & 2 of the magnetic code
            var _track1_regex = /%B?([0-9]*)\^([A-Z\/ -_]*)\^([0-9]{4})(.{3})([^?]+)\?/;

            var track1 = magtekInput.match(_track1_regex);
            var magtek_generated = magtekInput.split('|');

            var to_return = {};
            try {
                track1.shift(); // get rid of complete match
                to_return['number'] = track1.shift().substr(-4);
                to_return['name'] = track1.shift();
                track1.shift(); // expiration date
                track1.shift(); // service code
                track1.shift(); // discretionary data
                track1.shift(); // zero pad

                magtek_generated.shift(); // track1 and track2
                magtek_generated.shift(); // clear text crc
                magtek_generated.shift(); // encryption counter
                to_return['encrypted_block'] = magtek_generated.shift();
                magtek_generated.shift(); // enc session id
                magtek_generated.shift(); // device serial
                magtek_generated.shift(); // magneprint data
                magtek_generated.shift(); // magneprint status
                magtek_generated.shift(); // enc track3
                to_return['encrypted_key'] = magtek_generated.shift();
                magtek_generated.shift(); // enc track1
                magtek_generated.shift(); // reader enc status

                return to_return;
            } catch (e) {
                return 0;
            }
        },
        decodeMercuryResponse: function (data) {
            // get rid of xml version declaration and just keep the RStream
            // from the response because the xml contains two version
            // declarations. One for the SOAP, and one for the content. Maybe
            // we should unpack the SOAP layer in python?
            data = data.replace(/.*<\?xml version="1.0"\?>/, '');
            data = data.replace(/<\/CreditTransactionResult>.*/, '');

            var xml = $($.parseXML(data));
            var cmd_response = xml.find('CmdResponse');
            var tran_response = xml.find('TranResponse');

            return {
                status: cmd_response.find('CmdStatus').text(),
                message: cmd_response.find('TextResponse').text(),
                error: cmd_response.find('DSIXReturnCode').text(),
                card_type: tran_response.find('CardType').text(),
                auth_code: tran_response.find('AuthCode').text(),
                acq_ref_data: tran_response.find('AcqRefData').text(),
                process_data: tran_response.find('ProcessData').text(),
                invoice_no: tran_response.find('InvoiceNo').text(),
                ref_no: tran_response.find('RefNo').text(),
                record_no: tran_response.find('RecordNo').text(),
                purchase: parseFloat(tran_response.find('Purchase').text()),
                authorize: parseFloat(tran_response.find('Authorize').text()),
            };
        },
        isMercuryPayment(payment) {
            const paymentMethod = this.getRecord('pos.payment.method', payment.payment_method_id);
            return Boolean(paymentMethod.pos_mercury_config_id);
        },
    });

    return PointOfSaleModel;
});
