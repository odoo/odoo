/** @odoo-module */

import { PosStore } from "@point_of_sale/app/store/pos_store";
import { patch } from "@web/core/utils/patch";

patch(PosStore.prototype, {
    getOnlinePaymentMethods() {
        var online_payment_methods = [];

        $.each(this.models["pos.payment.method"].getAll(), function (i, payment_method) {
            if (payment_method.pos_mercury_config_id) {
                online_payment_methods.push({
                    label: payment_method.name,
                    item: payment_method.id,
                });
            }
        });

        return online_payment_methods;
    },
    decodeMagtek(magtekInput) {
        // Regular expression to identify and extract data from the track 1 & 2 of the magnetic code
        // FIXME: ` -_` is a character range from 32 to 95 which contains a lot of things and also covers `A-Z`
        //        this is almost certainly a mistake.
        var _track1_regex = /%B?([0-9]*)\^([A-Z/ -_]*)\^([0-9]{4})(.{3})([^?]+)\?/;

        var track1 = magtekInput.match(_track1_regex);
        var magtek_generated = magtekInput.split("|");

        var to_return = {};
        try {
            track1.shift(); // get rid of complete match
            to_return["number"] = track1.shift().substr(-4);
            to_return["name"] = track1.shift();
            track1.shift(); // expiration date
            track1.shift(); // service code
            track1.shift(); // discretionary data
            track1.shift(); // zero pad

            magtek_generated.shift(); // track1 and track2
            magtek_generated.shift(); // clear text crc
            magtek_generated.shift(); // encryption counter
            to_return["encrypted_block"] = magtek_generated.shift();
            magtek_generated.shift(); // enc session id
            magtek_generated.shift(); // device serial
            magtek_generated.shift(); // magneprint data
            magtek_generated.shift(); // magneprint status
            magtek_generated.shift(); // enc track3
            to_return["encrypted_key"] = magtek_generated.shift();
            magtek_generated.shift(); // enc track1
            magtek_generated.shift(); // reader enc status

            return to_return;
        } catch {
            return 0;
        }
    },
    decodeMercuryResponse(data) {
        // get rid of xml version declaration and just keep the RStream
        // from the response because the xml contains two version
        // declarations. One for the SOAP, and one for the content. Maybe
        // we should unpack the SOAP layer in python?
        data = data.replace(/.*<\?xml version="1.0"\?>/, "");
        data = data.replace(/<\/CreditTransactionResult>.*/, "");

        var xml = $($.parseXML(data));
        var cmd_response = xml.find("CmdResponse");
        var tran_response = xml.find("TranResponse");

        return {
            status: cmd_response.find("CmdStatus").text(),
            message: cmd_response.find("TextResponse").text(),
            error: cmd_response.find("DSIXReturnCode").text(),
            card_type: tran_response.find("CardType").text(),
            auth_code: tran_response.find("AuthCode").text(),
            acq_ref_data: tran_response.find("AcqRefData").text(),
            process_data: tran_response.find("ProcessData").text(),
            invoice_no: tran_response.find("InvoiceNo").text(),
            ref_no: tran_response.find("RefNo").text(),
            record_no: tran_response.find("RecordNo").text(),
            purchase: parseFloat(tran_response.find("Purchase").text()),
            authorize: parseFloat(tran_response.find("Authorize").text()),
        };
    },
});
