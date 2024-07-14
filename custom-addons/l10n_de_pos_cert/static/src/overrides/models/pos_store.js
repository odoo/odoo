/** @odoo-module */

import { Order } from "@point_of_sale/app/store/models";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { patch } from "@web/core/utils/patch";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";
import { OfflineErrorPopup } from "@point_of_sale/app/errors/popups/offline_error_popup";
import { ConfirmPopup } from "@point_of_sale/app/utils/confirm_popup/confirm_popup";
import { _t } from "@web/core/l10n/translation";

const RATE_ID_MAPPING = {
    1: "NORMAL",
    2: "REDUCED_1",
    3: "SPECIAL_RATE_1",
    4: "SPECIAL_RATE_2",
    5: "NULL",
};

patch(PosStore.prototype, {
    // @Override
    async setup() {
        this.token = "";
        this.vatRateMapping = {};
        await super.setup(...arguments);
    },
    //@Override
    async after_load_server_data() {
        if (this.isCountryGermanyAndFiskaly()) {
            await this.env.services.orm
                .call("pos.config", "l10n_de_get_fiskaly_urls_and_keys", [this.config.id])
                .then((data) => {
                    this.company.l10n_de_fiskaly_api_key = data["api_key"];
                    this.company.l10n_de_fiskaly_api_secret = data["api_secret"];
                    this.useKassensichvVersion2 = this.config.l10n_de_fiskaly_tss_id.includes("|");
                    this.apiUrl =
                        data["kassensichv_url"] +
                        "/api/v" +
                        (this.useKassensichvVersion2 ? "2" : "1"); // use correct version
                    return this.initVatRates(data["dsfinvk_url"] + "/api/v0");
                });
        }
        return super.after_load_server_data(...arguments);
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
        return this.company.l10n_de_fiskaly_api_key;
    },
    getApiSecret() {
        return this.company.l10n_de_fiskaly_api_secret;
    },
    getTssId() {
        return (
            this.config.l10n_de_fiskaly_tss_id && this.config.l10n_de_fiskaly_tss_id.split("|")[0]
        );
    },
    getClientId() {
        return this.config.l10n_de_fiskaly_client_id;
    },
    isUsingApiV2() {
        return this.useKassensichvVersion2;
    },
    isCountryGermany() {
        return this.config.is_company_country_germany;
    },
    isCountryGermanyAndFiskaly() {
        return this.isCountryGermany() && !!this.getTssId();
    },
    initVatRates(url) {
        const data = {
            api_key: this.getApiKey(),
            api_secret: this.getApiSecret(),
        };

        return $.ajax({
            url: url + "/auth",
            method: "POST",
            data: JSON.stringify(data),
            contentType: "application/json",
            timeout: 5000,
        }).then((data) => {
            const token = data.access_token;
            return $.ajax({
                url: url + "/vat_definitions",
                method: "GET",
                headers: { Authorization: `Bearer ${token}` },
                timeout: 5000,
            })
                .then((vat_data) => {
                    vat_data.data.forEach((vat_definition) => {
                        if (!(vat_definition.percentage in this.vatRateMapping)) {
                            this.vatRateMapping[vat_definition.percentage] =
                                RATE_ID_MAPPING[vat_definition.vat_definition_export_id];
                        }
                    });
                })
                .catch((error) => {
                    // This is a fallback where we hardcode the taxes hoping that they didn't change ...
                    this.vatRateMapping = {
                        19: "NORMAL",
                        7: "REDUCED_1",
                        10.7: "SPECIAL_RATE_1",
                        5.5: "SPECIAL_RATE_2",
                        0: "NULL",
                    };
                });
        });
    },
    //@Override
    /**
     * This function first attempts to send the orders remaining in the queue to Fiskaly before trying to
     * send it to Odoo. Two cases can happen:
     * - Failure to send to Fiskaly => we assume that if one order fails, EVERY order will fail
     * - Failure to send to Odoo => the order is already sent to Fiskaly, we store them locally with the TSS info
     */
    async _flush_orders(orders, options) {
        if (!this.isCountryGermanyAndFiskaly()) {
            return super._flush_orders(...arguments);
        }
        if (!orders || !orders.length) {
            return Promise.resolve([]);
        }

        const orderObjectMap = {};
        for (const orderJson of orders) {
            orderObjectMap[orderJson["id"]] = new Order(
                { env: this.env },
                { pos: this, json: orderJson["data"] }
            );
        }

        let fiskalyError;
        const sentToFiskaly = [];
        const fiskalyFailure = [];
        const ordersToUpdate = {};
        for (const orderJson of orders) {
            try {
                const orderObject = orderObjectMap[orderJson["id"]];
                if (!fiskalyError) {
                    if (orderObject.isTransactionInactive()) {
                        await orderObject.createTransaction();
                        ordersToUpdate[orderJson["id"]] = true;
                    }
                    if (orderObject.isTransactionStarted()) {
                        await orderObject.finishShortTransaction();
                        ordersToUpdate[orderJson["id"]] = true;
                    }
                }
                if (orderObject.isTransactionFinished()) {
                    sentToFiskaly.push(orderJson);
                } else {
                    fiskalyFailure.push(orderJson);
                }
            } catch (error) {
                fiskalyError = error;
                fiskalyError.code = "fiskaly";
                fiskalyFailure.push(orderJson);
            }
        }

        let result, odooError;
        if (sentToFiskaly.length > 0) {
            for (const orderJson of sentToFiskaly) {
                if (ordersToUpdate[orderJson["id"]]) {
                    orderJson["data"] = orderObjectMap[orderJson["id"]].export_as_JSON();
                }
            }
            try {
                result = await super._flush_orders(...arguments);
            } catch (error) {
                odooError = error;
            }
        }
        if (result && fiskalyFailure.length === 0) {
            return result;
        } else {
            if (Object.keys(ordersToUpdate).length) {
                for (const orderJson of fiskalyFailure) {
                    if (ordersToUpdate[orderJson["id"]]) {
                        orderJson["data"] = orderObjectMap[orderJson["id"]].export_as_JSON();
                    }
                }
                const ordersToSave =
                    result && result.length ? fiskalyFailure : fiskalyFailure.concat(sentToFiskaly);
                this.db.save("orders", ordersToSave);
            }
            this.set_synch("disconnected");
            throw odooError || fiskalyError;
        }
    },

    async fiskalyError(error, message) {
        if (error.status === 0) {
            const title = _t("No internet");
            const body = message.noInternet;
            await this.popup.add(OfflineErrorPopup, { title, body });
        } else if (error.status === 401 && error.source === "authenticate") {
            await this._showUnauthorizedPopup();
        } else if (
            (error.status === 400 && error.responseJSON.message.includes("tss_id")) ||
            (error.status === 404 && error.responseJSON.code === "E_TSS_NOT_FOUND")
        ) {
            await this._showBadRequestPopup("TSS ID");
        } else if (
            (error.status === 400 && error.responseJSON.message.includes("client_id")) ||
            (error.status === 400 && error.responseJSON.code === "E_CLIENT_NOT_FOUND")
        ) {
            // the api is actually sending an 400 error for a "Not found" error
            await this._showBadRequestPopup("Client ID");
        } else {
            const title = _t("Unknown error");
            const body = message.unknown;
            await this.popup.add(ErrorPopup, { title, body });
        }
    },
    async showFiskalyNoInternetConfirmPopup(event) {
        const { confirmed } = await this.popup.add(ConfirmPopup, {
            title: _t("Problem with internet"),
            body: _t(
                "You can either wait for the connection issue to be resolved or continue with a non-compliant receipt (the order will still be sent to Fiskaly once the connection issue is resolved).\n" +
                    "Do you want to continue with a non-compliant receipt?"
            ),
        });
        if (confirmed) {
            event.detail();
        }
    },
    async _showBadRequestPopup(data) {
        const title = _t("Bad request");
        const body = _t("Your %s is incorrect. Update it in your PoS settings", data);
        await this.popup.add(ErrorPopup, { title, body });
    },
    async _showUnauthorizedPopup() {
        const title = _t("Unauthorized error to Fiskaly");
        const body = _t(
            "It seems that your Fiskaly API key and/or secret are incorrect. Update them in your company settings."
        );
        await this.popup.add(ErrorPopup, { title, body });
    },
    async _showTaxError() {
        const rates = Object.keys(this.vatRateMapping);
        const title = _t("Tax error");
        let body;
        if (rates.length) {
            const ratesText = [rates.slice(0, -1).join(", "), rates.slice(-1)[0]].join(" and ");
            body = _t(
                "Product has an invalid tax amount. Only the following rates are allowed: %s.",
                ratesText
            );
        } else {
            body = _t(
                "There was an error while loading the Germany taxes. Try again later or your Fiskaly API key and secret might have been corrupted, request new ones"
            );
        }
        await this.popup.add(ErrorPopup, { title, body });
    },
});
