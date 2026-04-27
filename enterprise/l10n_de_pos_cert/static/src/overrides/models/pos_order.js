import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { convertFromEpoch } from "@l10n_de_pos_cert/app/utils";
import { patch } from "@web/core/utils/patch";
import { roundCurrency } from "@point_of_sale/app/models/utils/currency";

patch(PosOrder.prototype, {
    // @Override
    setup(vals) {
        super.setup(...arguments);
        if (this.isCountryGermanyAndFiskaly()) {
            this.uiState = {
                ...this.uiState,
                tx_revision: this.uiState.tx_revision || 1,
            };
            this.fiskalyUuid = this.fiskalyUuid || "";
            this.transactionState = this.transactionState || "inactive"; // Used to know when we need to create the fiskaly transaction

            // Init the tssInformation with the values from the config
            this.l10n_de_fiskaly_transaction_uuid = vals.l10n_de_fiskaly_transaction_uuid || false;
            this.l10n_de_fiskaly_transaction_number =
                vals.l10n_de_fiskaly_transaction_number || false;
            this.l10n_de_fiskaly_time_start = vals.l10n_de_fiskaly_time_start || false;
            this.l10n_de_fiskaly_time_end = vals.l10n_de_fiskaly_time_end || false;
            this.l10n_de_fiskaly_certificate_serial =
                vals.l10n_de_fiskaly_certificate_serial || false;
            this.l10n_de_fiskaly_timestamp_format = vals.l10n_de_fiskaly_timestamp_format || false;
            this.l10n_de_fiskaly_signature_value = vals.l10n_de_fiskaly_signature_value || false;
            this.l10n_de_fiskaly_signature_algorithm =
                vals.l10n_de_fiskaly_signature_algorithm || false;
            this.l10n_de_fiskaly_signature_public_key =
                vals.l10n_de_fiskaly_signature_public_key || false;
            this.l10n_de_fiskaly_client_serial_number =
                vals.l10n_de_fiskaly_client_serial_number || false;
        }
    },
    isCountryGermanyAndFiskaly() {
        return this.isCountryGermany() && !!this.getTssId();
    },
    getTssId() {
        return (
            this.config.l10n_de_fiskaly_tss_id && this.config.l10n_de_fiskaly_tss_id.split("|")[0]
        );
    },
    isCountryGermany() {
        return this.config.is_company_country_germany;
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
        return this.transactionState === "finished" || this.l10n_de_fiskaly_time_start;
    },
    // @Override
    export_for_printing(baseUrl, headerData) {
        const receipt = super.export_for_printing(...arguments);
        if (this.isCountryGermanyAndFiskaly()) {
            if (this.isTransactionFinished()) {
                receipt["tss"] = {
                    transaction_number: {
                        name: "TSE-Transaktion",
                        value: this.l10n_de_fiskaly_transaction_number,
                    },
                    number: { name: "Bonnummer", value: this.id },
                    time_start: { name: "TSE-Start", value: this.l10n_de_fiskaly_time_start },
                    time_end: { name: "TSE-Stop", value: this.l10n_de_fiskaly_time_end },
                    certificate_serial: {
                        name: "TSE-Seriennummer",
                        value: this.l10n_de_fiskaly_certificate_serial,
                    },
                    timestamp_format: {
                        name: "TSE-Zeitformat",
                        value: this.l10n_de_fiskaly_timestamp_format,
                    },
                    signature_value: {
                        name: "TSE-Signatur",
                        value: this.l10n_de_fiskaly_signature_value,
                    },
                    signature_algorithm: {
                        name: "TSE-Hashalgorithmus",
                        value: this.l10n_de_fiskaly_signature_algorithm,
                    },
                    signature_public_key: {
                        name: "TSE-PublicKey",
                        value: this.l10n_de_fiskaly_signature_public_key,
                    },
                    client_serial_number: {
                        name: "Client Serial No.",
                        value: this.l10n_de_fiskaly_client_serial_number,
                    },
                    erstBestellung: {
                        name: "TSE-Erstbestellung",
                        value: this.get_orderlines().length
                            ? this.get_orderlines()[0].get_product().display_name
                            : "Deposit",
                    },
                };
            } else {
                // When there is TSS server is unreachable
                receipt["tss_issue"] = true;
            }
        } else if (this.isCountryGermany() && !this.getTssId()) {
            receipt["test_environment"] = true;
        }
        return receipt;
    },
    /*
     *  Return an array of { 'payment_type': ..., 'amount': ...}
     */
    _createAmountPerPaymentTypeArray() {
        if (!this.payment_ids.length) {
            return [];
        }
        let cashDetailAmount = 0;
        let nonCashDetailAmount = 0;

        this.payment_ids.forEach((line) => {
            if (line.payment_method_id.type === "cash") {
                cashDetailAmount += line.amount;
            } else {
                nonCashDetailAmount += line.amount;
            }
        });

        // Reduce receivable payment which will be shown as paid when paid using deposit
        const adjustment = this.requiredSettlementAmount();
        const change = this.get_change();
        cashDetailAmount -= change;
        nonCashDetailAmount += adjustment;
        cashDetailAmount = roundCurrency(cashDetailAmount, this.currency).toFixed(2);
        nonCashDetailAmount = roundCurrency(nonCashDetailAmount, this.currency).toFixed(2);
        const cashDetail = { payment_type: "CASH", amount: cashDetailAmount };
        const nonCashDetail = { payment_type: "NON_CASH", amount: nonCashDetailAmount };

        return [cashDetail, nonCashDetail];
    },
    requiredSettlementAmount() {
        // Overall payment through receivable pm needs to be adjusted
        const totalReceivablePayment = this.payment_ids.reduce(
            (sum, line) => (!line.payment_method_id.journal_id ? sum + line.amount : sum),
            0
        );
        return -totalReceivablePayment;
    },
    _updateTimeStart(seconds) {
        this.l10n_de_fiskaly_time_start = convertFromEpoch(seconds);
    },
    _updateTssInfo(data) {
        this.l10n_de_fiskaly_transaction_number = data.number;
        this._updateTimeStart(data.time_start);
        this.l10n_de_fiskaly_time_end = convertFromEpoch(data.time_end);
        // certificate_serial is now called tss_serial_number in the v2 api
        this.l10n_de_fiskaly_certificate_serial = data.tss_serial_number
            ? data.tss_serial_number
            : data.certificate_serial;
        this.l10n_de_fiskaly_timestamp_format = data.log.timestamp_format;
        this.l10n_de_fiskaly_signature_value = data.signature.value;
        this.l10n_de_fiskaly_signature_algorithm = data.signature.algorithm;
        this.l10n_de_fiskaly_signature_public_key = data.signature.public_key;
        this.l10n_de_fiskaly_client_serial_number = data.client_serial_number;
        this.transactionFinished();
    },
});
