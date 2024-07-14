/** @odoo-module */

import { Order } from "@point_of_sale/app/store/models";
import { uuidv4 } from "@point_of_sale/utils";
import { convertFromEpoch } from "@l10n_de_pos_cert/app/utils";
import { TaxError } from "@l10n_de_pos_cert/app/errors";
import { patch } from "@web/core/utils/patch";

patch(Order.prototype, {
    // @Override
    setup() {
        super.setup(...arguments);
        if (this.pos.isCountryGermanyAndFiskaly()) {
            this.fiskalyUuid = this.fiskalyUuid || null;
            this.transactionState = this.transactionState || "inactive"; // Used to know when we need to create the fiskaly transaction
            this.tssInformation = this.tssInformation || this._initTssInformation();
            this.save_to_db();
        }
    },
    _initTssInformation() {
        return {
            transaction_number: { name: "TSE-Transaktion", value: null },
            time_start: { name: "TSE-Start", value: null },
            time_end: { name: "TSE-Stop", value: null },
            certificate_serial: { name: "TSE-Seriennummer", value: null },
            timestamp_format: { name: "TSE-Zeitformat", value: null },
            signature_value: { name: "TSE-Signatur", value: null },
            signature_algorithm: { name: "TSE-Hashalgorithmus", value: null },
            signature_public_key: { name: "TSE-PublicKey", value: null },
            client_serial_number: { name: "ClientID / KassenID", value: null },
            erstBestellung: { name: "TSE-Erstbestellung", value: null },
        };
    },
    isTransactionInactive() {
        return this.transactionState === "inactive";
    },
    transactionStarted() {
        this.transactionState = "started";
    },
    isTransactionStarted() {
        return this.transactionState === "started";
    },
    transactionFinished() {
        this.transactionState = "finished";
    },
    isTransactionFinished() {
        return this.transactionState === "finished" || this.tssInformation.time_start.value;
    },
    // @Override
    export_for_printing() {
        const receipt = super.export_for_printing(...arguments);
        if (this.pos.isCountryGermanyAndFiskaly()) {
            if (this.isTransactionFinished()) {
                receipt["tss"] = {};
                $.extend(true, receipt["tss"], this.tssInformation);
            } else {
                receipt["tss_issue"] = true;
            }
        } else if (this.pos.isCountryGermany() && !this.pos.getTssId()) {
            receipt["test_environment"] = true;
        }
        return receipt;
    },
    //@Override
    export_as_JSON() {
        const json = super.export_as_JSON(...arguments);
        if (this.pos.isCountryGermanyAndFiskaly()) {
            json["fiskaly_uuid"] = this.fiskalyUuid;
            json["transaction_state"] = this.transactionState;
            json["tss_info"] = {};
            for (var key in this.tssInformation) {
                if (key !== "erstBestellung") {
                    json["tss_info"][key] = this.tssInformation[key].value;
                }
            }
        }
        return json;
    },
    //@Override
    init_from_JSON(json) {
        this.state = json.state;
        super.init_from_JSON(...arguments);
        if (this.pos.isCountryGermanyAndFiskaly()) {
            this.fiskalyUuid = json.fiskaly_uuid;
            this.transactionState = json.transaction_state;
            if (json.tss_info) {
                this.tssInformation = this._initTssInformation();
                for (var key in json.tss_info) {
                    this.tssInformation[key].value = json.tss_info[key];
                }
                if (this.get_orderlines().length > 0) {
                    this.tssInformation.erstBestellung.value =
                        this.get_orderlines()[0].get_product().display_name;
                }
            }
        }
    },
    check_germany_taxes(product){
        if (this.pos.isCountryGermanyAndFiskaly()) {
            if (product.taxes_id.length === 0 || !(this.pos.taxes_by_id[product.taxes_id[0]].amount in this.pos.vatRateMapping)) {
                throw new TaxError(product);
            }
        }
    },
    //@Override
    async add_product(product, options) {
        this.check_germany_taxes(product);
        return super.add_product(...arguments);
    },
    //@override
    add_orderline(line) {
        if (line.order && !['paid', 'done', 'invoiced'].includes(line.order.state))
            this.check_germany_taxes(line.product);
        return super.add_orderline(...arguments);
    },
    _authenticate() {
        const data = {
            api_key: this.pos.getApiKey(),
            api_secret: this.pos.getApiSecret(),
        };

        return $.ajax({
            url: this.pos.getApiUrl() + "/auth",
            method: "POST",
            data: JSON.stringify(data),
            contentType: "application/json",
            timeout: 5000,
        })
            .then((data) => {
                this.pos.setApiToken(data.access_token);
            })
            .catch((error) => {
                error.source = "authenticate";
                return Promise.reject(error);
            });
    },
    async createTransaction() {
        if (!this.pos.getApiToken()) {
            await this._authenticate(); //  If there's an error, a promise is created with a rejected value
        }

        const transactionUuid = uuidv4();
        const data = {
            state: "ACTIVE",
            client_id: this.pos.getClientId(),
        };

        return $.ajax({
            url: `${this.pos.getApiUrl()}/tss/${this.pos.getTssId()}/tx/${transactionUuid}${
                this.pos.isUsingApiV2() ? "?tx_revision=1" : ""
            }`,
            method: "PUT",
            headers: { Authorization: `Bearer ${this.pos.getApiToken()}` },
            data: JSON.stringify(data),
            contentType: "application/json",
            timeout: 5000,
        })
            .then((data) => {
                this.fiskalyUuid = transactionUuid;
                this.transactionStarted();
            })
            .catch(async (error) => {
                if (error.status === 401) {
                    // Need to update the token
                    await this._authenticate();
                    return this.createTransaction();
                }
                // Return a Promise with rejected value for errors that are not handled here
                return Promise.reject(error);
            });
    },
    /*
     *  Return an array of { 'vat_rate': ..., 'amount': ...}
     */
    _createAmountPerVatRateArray() {
        const rateIds = {
            NORMAL: [],
            REDUCED_1: [],
            SPECIAL_RATE_1: [],
            SPECIAL_RATE_2: [],
            NULL: [],
        };
        this.get_tax_details().forEach((detail) => {
            rateIds[this.pos.vatRateMapping[detail.tax.amount]].push(detail.tax.id);
        });
        const amountPerVatRate = {
            NORMAL: 0,
            REDUCED_1: 0,
            SPECIAL_RATE_1: 0,
            SPECIAL_RATE_2: 0,
            NULL: 0,
        };
        for (var rate in rateIds) {
            rateIds[rate].forEach((id) => {
                amountPerVatRate[rate] += this.get_total_for_taxes(id);
            });
        }
        return Object.keys(amountPerVatRate)
            .filter((rate) => !!amountPerVatRate[rate])
            .map((rate) => ({
                vat_rate: rate,
                amount: this.env.utils.roundCurrency(amountPerVatRate[rate]).toFixed(2),
            }));
    },
    /*
     *  Return an array of { 'payment_type': ..., 'amount': ...}
     */
    _createAmountPerPaymentTypeArray() {
        const amountPerPaymentTypeArray = [];
        this.get_paymentlines().forEach((line) => {
            amountPerPaymentTypeArray.push({
                payment_type:
                    line.payment_method.name.toLowerCase() === "cash" ? "CASH" : "NON_CASH",
                amount: this.env.utils.roundCurrency(line.amount).toFixed(2),
            });
        });
        const change = this.get_change();
        if (change) {
            amountPerPaymentTypeArray.push({
                payment_type: "CASH",
                amount: this.env.utils.roundCurrency(-change).toFixed(2),
            });
        }
        return amountPerPaymentTypeArray;
    },
    _updateTimeStart(seconds) {
        this.tssInformation.time_start.value = convertFromEpoch(seconds);
    },
    _updateTssInfo(data) {
        this.tssInformation.transaction_number.value = data.number;
        this._updateTimeStart(data.time_start);
        this.tssInformation.time_end.value = convertFromEpoch(data.time_end);
        // certificate_serial is now called tss_serial_number in the v2 api
        this.tssInformation.certificate_serial.value = data.tss_serial_number
            ? data.tss_serial_number
            : data.certificate_serial;
        this.tssInformation.timestamp_format.value = data.log.timestamp_format;
        this.tssInformation.signature_value.value = data.signature.value;
        this.tssInformation.signature_algorithm.value = data.signature.algorithm;
        this.tssInformation.signature_public_key.value = data.signature.public_key;
        this.tssInformation.client_serial_number.value = data.client_serial_number;
        this.tssInformation.erstBestellung.value = this.get_orderlines()[0]
            ? this.get_orderlines()[0].get_product().display_name
            : undefined;
        this.transactionFinished();
    },
    async finishShortTransaction() {
        if (!this.pos.getApiToken()) {
            await this._authenticate();
        }

        const amountPerVatRateArray = this._createAmountPerVatRateArray();
        const amountPerPaymentTypeArray = this._createAmountPerPaymentTypeArray();
        const data = {
            state: "FINISHED",
            client_id: this.pos.getClientId(),
            schema: {
                standard_v1: {
                    receipt: {
                        receipt_type: "RECEIPT",
                        amounts_per_vat_rate: amountPerVatRateArray,
                        amounts_per_payment_type: amountPerPaymentTypeArray,
                    },
                },
            },
        };
        return $.ajax({
            headers: { Authorization: `Bearer ${this.pos.getApiToken()}` },
            url: `${this.pos.getApiUrl()}/tss/${this.pos.getTssId()}/tx/${this.fiskalyUuid}?${
                this.pos.isUsingApiV2() ? "tx_revision=2" : "last_revision=1"
            }`,
            method: "PUT",
            data: JSON.stringify(data),
            contentType: "application/json",
            timeout: 5000,
        })
            .then((data) => {
                this._updateTssInfo(data);
            })
            .catch(async (error) => {
                if (error.status === 401) {
                    // Need to update the token
                    await this._authenticate();
                    return this.finishShortTransaction();
                }
                // Return a Promise with rejected value for errors that are not handled here
                return Promise.reject(error);
            });
    },
    async cancelTransaction() {
        if (!this.pos.getApiToken()) {
            await this._authenticate();
        }

        const data = {
            state: "CANCELLED",
            client_id: this.pos.getClientId(),
            schema: {
                standard_v1: {
                    receipt: {
                        receipt_type: "CANCELLATION",
                        amounts_per_vat_rate: [],
                    },
                },
            },
        };

        return $.ajax({
            url: `${this.pos.getApiUrl()}/tss/${this.pos.getTssId()}/tx/${this.fiskalyUuid}?${
                this.pos.isUsingApiV2() ? "tx_revision=2" : "last_revision=1"
            }`,
            method: "PUT",
            headers: { Authorization: `Bearer ${this.pos.getApiToken()}` },
            data: JSON.stringify(data),
            contentType: "application/json",
            timeout: 5000,
        }).catch(async (error) => {
            if (error.status === 401) {
                // Need to update the token
                await this._authenticate();
                return this.cancelTransaction();
            }
            // Return a Promise with rejected value for errors that are not handled here
            return Promise.reject(error);
        });
    },
});
