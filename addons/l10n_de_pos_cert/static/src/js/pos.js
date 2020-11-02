odoo.define('l10n_de_pos_cert.pos', function(require) {
    "use strict";

    const models = require('point_of_sale.models');
    const { uuidv4 } = require('l10n_de_pos_cert.utils');
    const { convertFromEpoch } = require('l10n_de_pos_cert.utils');

    const rateMapping = {
        16: 'NORMAL',
        19: 'NORMAL',
        5:  'REDUCED_1',
        7:  'REDUCED_1',
        0:  'NULL',
    };

    models.load_fields('res.company', ['fiskaly_key', 'fiskaly_secret']);

    let _super_posmodel = models.PosModel.prototype;
    models.PosModel = models.PosModel.extend({
        // @Override
        initialize(attributes) {
            _super_posmodel.initialize.apply(this,arguments);
            this.token = '';
            this.apiUrl = 'https://kassensichv.io/api/v1/';
        },
        getApiToken() {
            return this.token;
        },
        setApiToken(token) {
            this.token = token;
        },
        getApiUrl() {
            return this.apiUrl;
        },
        getApiKey() {
            return this.company.fiskaly_key;
        },
        getApiSecret() {
            return this.company.fiskaly_secret;
        },
        getTssId() {
            return this.config.fiskaly_tss_id;
        },
        getClientId() {
            return this.config.fiskaly_client_id;
        }
    });

    var _super_order = models.Order.prototype;
    models.Order = models.Order.extend({
        // @Override
        initialize() {
            _super_order.initialize.apply(this,arguments);
            this.fiskalyUuid = this.fiskalyUuid || uuidv4();
            this.txLastRevision = this.txLastRevision || null;
            this.transactionState = this.transactionState || 'inactive'; // Used to know when we need to create the fiskaly transaction
            this.tssInformation = this.tssInformation || {
                'number': { 'name': 'TSE-Transaktion', 'value': null },
                'timeStart': { 'name': 'TSE-Start', 'value': null },
                'timeEnd': { 'name': 'TSE-Stop', 'value': null },
                'certificateSerial': { 'name': 'TSE-Seriennummer', 'value': null },
                'timestampFormat': { 'name': 'TSE-Zeitformat', 'value': null },
                'signatureValue': { 'name': 'TSE-Signatur', 'value': null },
                'signatureAlgorithm': { 'name': 'TSE-Hashalgorithmus', 'value': null },
                'signaturePublicKey': { 'name': 'TSE-PublicKey', 'value': null },
                'clientSerialnumber': { 'name': 'ClientID / KassenID', 'value': null },
                'erstBestellung': { 'name': 'TSE-Erstbestellung', 'value': null } // ???? Todo TBD => first article
            };
            this.save_to_db();
        },
        isTransactionInactive() {
            return this.transactionState == 'inactive';
        },
        transactionStarted() {
            this.transactionState = 'started';
        },
        isTransactionStarted() {
            return this.transactionState == 'started';
        },
        transactionFinished() {
            this.transactionState = 'finished';
        },
        isTransactionFinished() {
            return this.transactionState == 'finished';
        },
        setLastRevision(revision) {
            this.txLastRevision = revision;
        },
        getLastRevision() {
            return this.txLastRevision;
        },
        // @Override
        export_for_printing() {
            const receipt = _super_order.export_for_printing.apply(this, arguments);
            receipt['tss'] = {};
            $.extend(true, receipt['tss'], this.tssInformation);
            return receipt;
        },
        //@Override
        export_as_JSON() {
            const json = _super_order.export_as_JSON.apply(this, arguments);
            json['fiskaly_uuid'] = this.fiskalyUuid;
            json['transaction_state'] = this.transactionState;
            if (this.txLastRevision) {
                json['last_revision'] = this.txLastRevision;
            }
            if (this.isTransactionFinished()) {
                json['tss_info'] = {};
                for (var key in this.tssInformation) {
                    if (key !== 'erstBestellung') {
                        json['tss_info'][key] = this.tssInformation[key].value;
                    }
                }

            }
            return json;
        },
        //@Override
        init_from_JSON(json) {
            _super_order.init_from_JSON.apply(this, arguments);
            this.fiskalyUuid = json.fiskaly_uuid;
            this.transactionState = json.transaction_state;
            if (json.last_revision) {
                this.txLastRevision = json.last_revision;
            }
            if (this.isTransactionFinished()) {
                for (var key in json.tss_info) {
                    this.tssInformation[key].value = json.tss_info[key];
                }
                this.tssInformation.erstBestellung.value = this.get_orderlines()[0].get_full_product_name();
            }
        },
        _authenticate() {
            return $.ajax({
                url: this.pos.getApiUrl() + 'auth',
                method: 'POST',
                data: {
                    'api_key': this.pos.getApiKey(),
                    'api_secret': this.pos.getApiSecret()
                }
            }).then((data) => {
                this.pos.setApiToken(data.access_token);
            }).catch((error) => {
                error.source = 'authenticate';
                return Promise.reject(error);
            });
        },
        async createTransaction() {
            if (!this.pos.getApiToken()) {
                await this._authenticate(); //  If there's an error, a promise is created with a rejected value
            }

            const data = {
                'state': 'ACTIVE',
                'client_id': this.pos.getClientId()
            };

            return $.ajax({
                url: `${this.pos.getApiUrl()}tss/${this.pos.getTssId()}/tx/${this.fiskalyUuid}`,
                method: 'PUT',
                headers: {
                    'Authorization': `Bearer ${this.pos.getApiToken()}`
                },
                data: JSON.stringify(data),
                contentType: 'application/json'
            }).then((data) => {
                this.txLastRevision = data.latest_revision;
                this.transactionStarted();
                this.trigger('change');
            }).catch(async (error) => {
                if (error.status === 401) {  // Need to update the token
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
                'NORMAL': [],
                'REDUCED_1': [],
                'NULL': [],
            };
            this.get_tax_details().forEach((detail) => {
                rateIds[rateMapping[detail.tax.amount]].push(detail.tax.id);
            });
            const amountPerVatRate = { 'NORMAL': 0, 'REDUCED_1': 0, 'NULL': 0 };
            for (var rate in rateIds) {
                rateIds[rate].forEach((id) => {
                    amountPerVatRate[rate] += this.get_total_for_taxes(id);
                });
            }
            return Object.keys(amountPerVatRate).filter((rate) => !!amountPerVatRate[rate])
                .map((rate) => ({ 'vat_rate': rate, 'amount': amountPerVatRate[rate].toFixed(2) }));
        },
        /*
         *  Return an array of { 'payment_type': ..., 'amount': ...}
         */
        _createAmountPerPaymentTypeArray() {
            const amountPerPaymentTypeArray = [];
            this.get_paymentlines().forEach((line) => {
                amountPerPaymentTypeArray.push({
                    'payment_type': line.payment_method.name.toLowerCase() === 'cash' ? 'CASH' : 'NON_CASH',
                    'amount' : line.amount.toFixed(2)
                 });
            });
            const change = this.get_change();
            if (!!change) {
                amountPerPaymentTypeArray.push({
                    'payment_type': 'CASH',
                    'amount': (-change).toFixed(2)
                });
            }
            return amountPerPaymentTypeArray;
        },
        async finishShortTransaction() {
            if (!this.pos.getApiToken()) {
                await this._authenticate();
            }

            const amountPerVatRateArray = this._createAmountPerVatRateArray();
            const amountPerPaymentTypeArray = this._createAmountPerPaymentTypeArray();
            const data = {
                'state': 'FINISHED',
                'client_id': this.pos.getClientId(),
                'schema': {
                    'standard_v1': {
                        'receipt': {
                            'receipt_type': 'RECEIPT',
                            'amounts_per_vat_rate': amountPerVatRateArray,
                            'amounts_per_payment_type': amountPerPaymentTypeArray
                        }
                    }
                }
            };
            return $.ajax({
                headers: {
                    'Authorization': `Bearer ${this.pos.getApiToken()}`
                },
                url: `${this.pos.getApiUrl()}tss/${this.pos.getTssId()}/tx/${this.fiskalyUuid}?last_revision=${this.txLastRevision}`,
                method: 'PUT',
                data: JSON.stringify(data),
                contentType: 'application/json'
            }).then((data) => {
                this.tssInformation.number.value = data.number;
                this.tssInformation.timeStart.value = convertFromEpoch(data.time_start);
                this.tssInformation.timeEnd.value = convertFromEpoch(data.time_end);
                this.tssInformation.certificateSerial.value = data.certificate_serial;
                this.tssInformation.timestampFormat.value = data.log.timestamp_format;
                this.tssInformation.signatureValue.value = data.signature.value;
                this.tssInformation.signatureAlgorithm.value = data.signature.algorithm;
                this.tssInformation.signaturePublicKey.value = data.signature.public_key;
                this.tssInformation.clientSerialnumber.value = data.client_serial_number;
                this.tssInformation.erstBestellung.value = this.get_orderlines()[0].get_full_product_name();
                this.transactionFinished();
            }).catch(async (error) => {
                if (error.status === 401) {  // Need to update the token
                    await this._authenticate();
                    return this.finishShortTransaction();
                }
                // Return a Promise with rejected value for errors that are not handled here
                return Promise.reject(error);
            });;
        },
        async cancelTransaction() {
            if (!this.pos.getApiToken()) {
                await this._authenticate();
            }

            const data = {
                'state': 'CANCELLED',
                'client_id': this.pos.getClientId(),
                'schema': {
                    'standard_v1': {
                        'receipt': {
                            'receipt_type': 'CANCELLATION',
                            'amounts_per_vat_rate': []
                       }
                    }
                }
            };

            return $.ajax({
                url: `${this.pos.getApiUrl()}tss/${this.pos.getTssId()}/tx/${this.fiskalyUuid}?last_revision=${this.txLastRevision}`,
                method: 'PUT',
                headers: {
                    'Authorization': `Bearer ${this.pos.getApiToken()}`
                },
                data: JSON.stringify(data),
                contentType: 'application/json'
            }).catch(async (error) => {
                if (error.status === 401) {  // Need to update the token
                    await this._authenticate();
                    return this.cancelTransaction();
                }
                // Return a Promise with rejected value for errors that are not handled here
                return Promise.reject(error);
            });;
        }
    });
});
