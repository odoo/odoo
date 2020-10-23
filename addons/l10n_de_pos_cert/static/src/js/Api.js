odoo.define('l10n_de_pos_cert.Api', function(require) {

    const { convertFromEpoch } = require('l10n_de_pos_cert.utils');

    const rateMapping = {
        16: 'NORMAL',
        19: 'NORMAL',
        5:  'REDUCED_1',
        7:  'REDUCED_1',
        0:  'NULL',
    };


    class Api {
        constructor() {
            this.apiUrl = 'https://kassensichv.io/api/v1/';
            this.apiKey = 'test_datmep1287arrcsn9xgedq71f_test';
            this.apiSecret = '9snVgnaJ0Rk4uOTR5fGjHIWaTHVQqGCk9WaDk8j3f1d';
            this.token = '';
            this.tssId = '55d84f16-78f0-4d1d-9e5d-4e723ce7ac6f';
            this.clientId = '88b7278e-a6df-4103-b939-7843538a1f6d';
        }
        _authenticate() {
            console.log("authenticate");
            return $.ajax({
                url: this.apiUrl + 'auth',
                method: 'POST',
                data: {
                    'api_key': this.apiKey,
                    'api_secret': this.apiSecret
                }
            }).then((data) => {
                this.token = data.access_token;
            }).catch(() => {
                setTimeout(this._authenticate, 3000);
            });
        }
        async createTransaction(order) {
            console.log("create");
            if (!this.token) {
                await this._authenticate();
            }
            return $.ajax({
                url: `${this.apiUrl}tss/${this.tssId}/tx/${order.getUuid()}`,
                method: 'PUT',
                headers: {
                    'Authorization': `Bearer ${this.token}`
                },
                data: {
                    'state': 'ACTIVE',
                    'client_id': this.clientId
                },
            }).then(function(data) {
                order.setLastRevision(data.latest_revision);
            }).catch(async (error) => {
                if (error.status === 401) {
                    await this._authenticate();
                    return this.createTransaction(order);
                }
            });
        }
        /*
         *  Return an array of { 'vat_rate': ..., 'amount': ...}
         */
        _createAmountPerVatRateArray(order) {
            const rateIds = {
                'NORMAL': [],
                'REDUCED_1': [],
                'NULL': [],
            };
            order.get_tax_details().forEach((detail) => {
                rateIds[rateMapping[detail.tax.amount]].push(detail.tax.id);
            });
            const amountPerVatRate = { 'NORMAL': 0, 'REDUCED_1': 0, 'NULL': 0 };
            for (var rate in rateIds) {
                rateIds[rate].forEach((id) => {
                    amountPerVatRate[rate] += order.get_total_for_taxes(id);
                });
            }
            return Object.keys(amountPerVatRate).filter((rate) => !!amountPerVatRate[rate])
                .map((rate) => ({ 'vat_rate': rate, 'amount': amountPerVatRate[rate].toFixed(2) }));
        }
        /*
         *  Return an array of { 'payment_type': ..., 'amount': ...}
         */
        _createAmountPerPaymentTypeArray(order) {
            const amountPerPaymentTypeArray = [];
            order.get_paymentlines().forEach((line) => {
                amountPerPaymentTypeArray.push({
                    'payment_type': line.payment_method.name.toLowerCase() === 'cash' ? 'CASH' : 'NON_CASH',
                    'amount' : line.amount.toFixed(2)
                 });
            });
            const change = order.get_change();
            if (!!change) {
                amountPerPaymentTypeArray.push({
                    'payment_type': 'CASH',
                    'amount': (-change).toFixed(2)
                });
            }
            return amountPerPaymentTypeArray;
        }
        async finishShortTransaction(order) {
            if (!this.token) {
                await this._authenticate();
            }

            const amountPerVatRateArray = this._createAmountPerVatRateArray(order);
            const amountPerPaymentTypeArray = this._createAmountPerPaymentTypeArray(order);
            return $.ajax({
                headers: {
                    'Authorization': `Bearer ${this.token}`
                },
                url: `${this.apiUrl}tss/${this.tssId}/tx/${order.getUuid()}?last_revision=${order.getLastRevision()}`,
                method: 'PUT',
                data: {
                    'state': 'FINISHED',
                    'client_id': this.clientId,
                    'schema': {
                        'standard_v1': {
                            'receipt': {
                                'receipt_type': 'RECEIPT',
                                'amounts_per_vat_rate': amountPerVatRateArray,
                                'amounts_per_payment_type': amountPerPaymentTypeArray
                            }
                        }
                    }
                },
            }).then(function(data) {
                order.setTseInformation('number', data.number);
                order.setTseInformation('timeStart', convertFromEpoch(data.time_start));
                order.setTseInformation('timeEnd', convertFromEpoch(data.time_end));
                order.setTseInformation('certificateSerial', data.certificate_serial);
                order.setTseInformation('timestampFormat', data.log.timestamp_format);
                order.setTseInformation('signatureValue', data.signature.value);
                order.setTseInformation('signatureAlgorithm', data.signature.algorithm);
                order.setTseInformation('signaturePublickKey', data.signature.public_key);
                order.setTseInformation('clientSerialnumber', data.client_serial_number);
                console.log("GG REQUEST SENT");
            }).catch(function() {
                console.log("rip");
            });
        }
    }

    return new Api();

});