/** @odoo-module */

import { PosGlobalState } from "@point_of_sale/js/models";
import { pos_env as legacyEnv } from "@point_of_sale/js/pos_env";

import { registry } from "@web/core/registry";
import { ConfirmPopup } from "@point_of_sale/js/Popups/ConfirmPopup";
import { reactive, markRaw } from "@odoo/owl";
import { Reactive } from "@point_of_sale/utils";
import { identifyError } from "@point_of_sale/app/error_handlers/error_handlers";
import { ConnectionLostError } from "@web/core/network/rpc_service";
import { ErrorPopup } from "@point_of_sale/js/Popups/ErrorPopup";
import { _t } from "@web/core/l10n/translation";
import { CashOpeningPopup } from "@point_of_sale/js/Popups/CashOpeningPopup";

export class PosStore extends Reactive {
    /** @type {'LOADING' | 'READY' | 'CLOSING'} */
    uiState = "LOADING";
    hasBigScrollBars = false;
    loadingSkipButtonIsShown = false;
    mainScreen = { name: null, component: null };
    tempScreen = null;
    legacyEnv = legacyEnv;
    globalState = new PosGlobalState({ env: markRaw(legacyEnv) });

    static serviceDependencies = ["popup", "orm", "number_buffer"];
    constructor({ popup, orm, number_buffer }) {
        super();
        this.orm = orm;
        this.popup = popup;
        this.numberBuffer = number_buffer;
        this.setup();
    }
    // use setup instead of constructor because setup can be patched.
    setup() {}

    showScreen(name, props) {
        const component = registry.category("pos_screens").get(name);
        this.mainScreen = { component, props };
        // Save the screen to the order so that it is shown again when the order is selected.
        if (component.storeOnOrder ?? true) {
            this.globalState.get_order()?.set_screen_data({ name, props });
        }
    }

    closeScreen() {
        const { name: screenName } = this.globalState.get_order().get_screen_data();
        this.showScreen(screenName);
    }

    connect_to_proxy() {
        return new Promise((resolve, reject) => {
            this.globalState.env.barcode_reader.disconnect_from_proxy();
            this.globalState.loadingSkipButtonIsShown = true;
            this.globalState.env.proxy
                .autoconnect({
                    force_ip: this.globalState.config.proxy_ip || undefined,
                    progress: function (prog) {},
                })
                .then(
                    () => {
                        if (this.globalState.config.iface_scan_via_proxy) {
                            this.globalState.env.barcode_reader.connect_to_proxy();
                        }
                        resolve();
                    },
                    (statusText, url) => {
                        // this should reject so that it can be captured when we wait for pos.ready
                        // in the chrome component.
                        // then, if it got really rejected, we can show the error.
                        if (statusText == "error" && window.location.protocol == "https:") {
                            reject({
                                title: _t("HTTPS connection to IoT Box failed"),
                                body: _.str.sprintf(
                                    _t(
                                        "Make sure you are using IoT Box v18.12 or higher. Navigate to %s to accept the certificate of your IoT Box."
                                    ),
                                    url
                                ),
                                popup: "alert",
                            });
                        } else {
                            resolve();
                        }
                    }
                );
        });
    }

    async closePos() {
        // If pos is not properly loaded, we just go back to /web without
        // doing anything in the order data.
        if (!this.globalState || this.globalState.db.get_orders().length === 0) {
            window.location = "/web#action=point_of_sale.action_client_pos_menu";
        }

        if (this.globalState.db.get_orders().length) {
            // If there are orders in the db left unsynced, we try to sync.
            // If sync successful, close without asking.
            // Otherwise, ask again saying that some orders are not yet synced.
            try {
                await this.globalState.push_orders();
                window.location = "/web#action=point_of_sale.action_client_pos_menu";
            } catch (error) {
                console.warn(error);
                const reason = this.globalState.failed
                    ? _t(
                          "Some orders could not be submitted to " +
                              "the server due to configuration errors. " +
                              "You can exit the Point of Sale, but do " +
                              "not close the session before the issue " +
                              "has been resolved."
                      )
                    : _t(
                          "Some orders could not be submitted to " +
                              "the server due to internet connection issues. " +
                              "You can exit the Point of Sale, but do " +
                              "not close the session before the issue " +
                              "has been resolved."
                      );
                const { confirmed } = await this.popup.add(ConfirmPopup, {
                    title: _t("Offline Orders"),
                    body: reason,
                });
                if (confirmed) {
                    // FIXME POSREF setting the location prevents the next render, the loading screen never shows
                    this.globalState.uiState = "CLOSING";
                    this.globalState.loadingSkipButtonIsShown = false;
                    window.location = "/web#action=point_of_sale.action_client_pos_menu";
                }
            }
        }
    }
    async closeSession(defaultCashCounted, notes, otherPaymentMethods, payments) {
        let response;

        if (this.globalState.config.cashControl) {
            response = await this.orm.call(
                "pos.session",
                "post_closing_cash_details"[this.globalState.pos_session.id],
                {
                    counted_cash: defaultCashCounted,
                }
            );

            if (!response.successful) {
                return this.handleClosingError(response);
            }
        }

        try {
            await this.orm.call("pos.session", "update_closing_control_state_session", [
                this.globalState.pos_session.id,
                notes,
            ]);
        } catch (error) {
            // We have to handle the error manually otherwise the validation check stops the script.
            // In case of "rescue session", we want to display the next popup with "handleClosingError".
            // FIXME
            if (
                !error.message &&
                !error.message.data &&
                error.message.data.message !== "This session is already closed."
            ) {
                throw error;
            }
        }

        try {
            const bankPaymentMethodDiffPairs = otherPaymentMethods
                .filter((pm) => pm.type == "bank")
                .map((pm) => [pm.id, payments[pm.id].difference]);
            response = await this.orm.call("pos.session", "close_session_from_ui", [
                this.globalState.pos_session.id,
                bankPaymentMethodDiffPairs,
            ]);
            if (!response.successful) {
                return this.handleClosingError(response);
            }
            window.location = "/web#action=point_of_sale.action_client_pos_menu";
        } catch (error) {
            if (identifyError(error) instanceof ConnectionLostError) {
                // Cannot redirect to backend when offline, let error handlers show the offline popup
                // FIXME POSREF: doing this means closing again when online will redo the beginning of the method
                // although it's impossible to close again because this.closeSessionClicked isn't reset to false
                // The application state is corrupted.
                throw error;
            } else {
                // FIXME POSREF: why are we catching errors here but not anywhere else in this method?
                await this.popup.add(ErrorPopup, {
                    title: _t("Closing session error"),
                    body: _t(
                        "An error has occurred when trying to close the session.\n" +
                            "You will be redirected to the back-end to manually close the session."
                    ),
                });
                window.location = "/web#action=point_of_sale.action_client_pos_menu";
            }
        }
    }
    async selectPartner() {
        // FIXME, find order to refund when we are in the ticketscreen.
        const currentOrder = this.globalState.get_order();
        if (!currentOrder) {
            return;
        }
        const currentPartner = currentOrder.get_partner();
        if (currentPartner && currentOrder.getHasRefundLines()) {
            this.popup.add(ErrorPopup, {
                title: this.env._t("Can't change customer"),
                body: _.str.sprintf(
                    this.env._t(
                        "This order already has refund lines for %s. We can't change the customer associated to it. Create a new order for the new customer."
                    ),
                    currentPartner.name
                ),
            });
            return;
        }
        const { confirmed, payload: newPartner } = await this.showTempScreen("PartnerListScreen", {
            partner: currentPartner,
        });
        if (confirmed) {
            currentOrder.set_partner(newPartner);
            currentOrder.updatePricelist(newPartner);
        }
    }
    // FIXME: POSREF, method exist only to be overrided
    async addProductFromUi(product, options) {
        this.globalState.get_order().add_product(product, options);
    }
    async addProductToCurrentOrder(product) {
        if (Number.isInteger(product)) {
            product = this.globalState.db.get_product_by_id(product);
        }
        const currentOrder = this.globalState.get_order();

        if (!currentOrder) {
            this.globalState.add_new_order();
        }

        const options = await product.getAddProductOptions();

        if (!options) {
            return;
        }

        // Add the product after having the extra information.
        this.addProductFromUi(product, options);
        this.numberBuffer.reset();
    }
    // FIXME POSREF get rid of temp screens entirely?
    showTempScreen(name, props = {}) {
        return new Promise((resolve) => {
            this.tempScreen = {
                name,
                component: registry.category("pos_screens").get(name),
                props: { ...props, resolve },
            };
        });
    }

    closeTempScreen() {
        this.tempScreen = null;
    }
    openCashControl() {
        if (this.shouldShowCashControl()) {
            this.popup.add(CashOpeningPopup, { keepBehind: true });
        }
    }
    shouldShowCashControl() {
        return (
            this.globalState.config.cash_control &&
            this.globalState.pos_session.state == "opening_control"
        );
    }
}

export const posService = {
    dependencies: PosStore.serviceDependencies,
    start(env, deps) {
        return reactive(new PosStore(deps));
    },
};

registry.category("services").add("pos", posService);
