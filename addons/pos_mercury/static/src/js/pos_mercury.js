/** @odoo-module */

import { PosGlobalState, Order, Payment } from "@point_of_sale/js/models";
import Registries from "@point_of_sale/js/Registries";

const PosMercuryPosGlobalState = (PosGlobalState) =>
    class PosMercuryPosGlobalState extends PosGlobalState {
        getOnlinePaymentMethods() {
            var online_payment_methods = [];

            $.each(this.payment_methods, function (i, payment_method) {
                if (payment_method.pos_mercury_config_id) {
                    online_payment_methods.push({
                        label: payment_method.name,
                        item: payment_method.id,
                    });
                }
            });

            return online_payment_methods;
        }
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
        }
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
        }
    };
Registries.Model.extend(PosGlobalState, PosMercuryPosGlobalState);

const PosMercuryPayment = (Payment) =>
    class PosMercuryPayment extends Payment {
        init_from_JSON(json) {
            super.init_from_JSON(...arguments);

            this.paid = json.paid;
            this.mercury_card_number = json.mercury_card_number;
            this.mercury_card_brand = json.mercury_card_brand;
            this.mercury_card_owner_name = json.mercury_card_owner_name;
            this.mercury_ref_no = json.mercury_ref_no;
            this.mercury_record_no = json.mercury_record_no;
            this.mercury_invoice_no = json.mercury_invoice_no;
            this.mercury_auth_code = json.mercury_auth_code;
            this.mercury_data = json.mercury_data;
            this.mercury_swipe_pending = json.mercury_swipe_pending;

            this.set_credit_card_name();
        }
        export_as_JSON() {
            return _.extend(super.export_as_JSON(...arguments), {
                paid: this.paid,
                mercury_card_number: this.mercury_card_number,
                mercury_card_brand: this.mercury_card_brand,
                mercury_card_owner_name: this.mercury_card_owner_name,
                mercury_ref_no: this.mercury_ref_no,
                mercury_record_no: this.mercury_record_no,
                mercury_invoice_no: this.mercury_invoice_no,
                mercury_auth_code: this.mercury_auth_code,
                mercury_data: this.mercury_data,
                mercury_swipe_pending: this.mercury_swipe_pending,
            });
        }
        set_credit_card_name() {
            if (this.mercury_card_number) {
                this.name = this.mercury_card_brand + " (****" + this.mercury_card_number + ")";
            }
        }
        is_done() {
            var res = super.is_done(...arguments);
            return res && !this.mercury_swipe_pending;
        }
        export_for_printing() {
            const result = super.export_for_printing(...arguments);
            result.mercury_data = this.mercury_data;
            result.mercury_auth_code = this.mercury_auth_code;
            return result;
        }
    };
Registries.Model.extend(Payment, PosMercuryPayment);

const PosMercuryOrder = (Order) =>
    class PosMercuryOrder extends Order {
        electronic_payment_in_progress() {
            var res = super.electronic_payment_in_progress(...arguments);
            return res || this.get_paymentlines().some((line) => line.mercury_swipe_pending);
        }
    };
Registries.Model.extend(Order, PosMercuryOrder);
