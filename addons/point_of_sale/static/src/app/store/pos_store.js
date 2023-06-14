/** @odoo-module */

import { PosGlobalState } from "@point_of_sale/app/store/models";

import { registry } from "@web/core/registry";
import { ConfirmPopup } from "@point_of_sale/app/utils/confirm_popup/confirm_popup";
import { Reactive } from "@web/core/utils/reactive";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";
import { _t } from "@web/core/l10n/translation";
import { CashOpeningPopup } from "@point_of_sale/app/store/cash_opening_popup/cash_opening_popup";
import { sprintf } from "@web/core/utils/strings";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";

export class PosStore extends Reactive {
    hasBigScrollBars = false;
    loadingSkipButtonIsShown = false;
    mainScreen = { name: null, component: null };
    tempScreen = null;

    static serviceDependencies = [
        "popup",
        "orm",
        "number_buffer",
        "barcode_reader",
        "hardware_proxy",
    ];
    constructor() {
        super();
        this.ready = this.setup(...arguments).then(() => this);
    }
    // use setup instead of constructor because setup can be patched.
    async setup(env, { popup, orm, number_buffer, hardware_proxy, barcode_reader }) {
        this.orm = orm;
        this.popup = popup;
        this.numberBuffer = number_buffer;
        this.barcodeReader = barcode_reader;
        this.globalState = new PosGlobalState({ orm, env, hardwareProxy: hardware_proxy });
        this.hardwareProxy = hardware_proxy;
        // FIXME POSREF: the hardwareProxy needs the pos and the pos needs the hardwareProxy. Maybe
        // the hardware proxy should just be part of the pos service?
        this.hardwareProxy.pos = this.globalState;
        await this.globalState.load_server_data();
        if (this.globalState.config.use_proxy) {
            await this.connectToProxy();
        }
        this.closeOtherTabs();
        this.preloadImages();
        this.showScreen("ProductScreen");
    }

    showScreen(name, props) {
        const component = registry.category("pos_screens").get(name);
        this.mainScreen = { component, props };
        // Save the screen to the order so that it is shown again when the order is selected.
        if (component.storeOnOrder ?? true) {
            this.globalState.get_order()?.set_screen_data({ name, props });
        }
    }

    // Now the printer should work in PoS without restaurant
    async sendOrderInPreparation(order, cancelled = false) {
        if (this.globalState.printers_category_ids_set.size) {
            try {
                const changes = order.changesToOrder(cancelled);

                if (changes.cancelled.length > 0 || changes.new.length > 0) {
                    const isPrintSuccessful = await order.printChanges(cancelled);
                    if (!isPrintSuccessful) {
                        this.popup.add(ErrorPopup, {
                            title: _t("Printing failed"),
                            body: _t("Failed in printing the changes in the order"),
                        });
                    }
                }
            } catch (e) {
                console.warn("Failed in printing the changes in the order", e);
            }
        }
        order.updateLastOrderChange();
    }
    closeScreen() {
        this.addOrderIfEmpty();
        const { name: screenName } = this.globalState.get_order().get_screen_data();
        this.showScreen(screenName);
    }

    addOrderIfEmpty() {
        if (!this.globalState.get_order()) {
            this.globalState.add_new_order();
        }
    }

    connectToProxy() {
        return new Promise((resolve, reject) => {
            this.barcodeReader?.disconnectFromProxy();
            this.globalState.loadingSkipButtonIsShown = true;
            this.hardwareProxy.autoconnect({ force_ip: this.globalState.config.proxy_ip }).then(
                () => {
                    if (this.globalState.config.iface_scan_via_proxy) {
                        this.barcodeReader?.connectToProxy();
                    }
                    resolve();
                },
                (statusText, url) => {
                    // this should reject so that it can be captured when we wait for pos.ready
                    // in the chrome component.
                    // then, if it got really rejected, we can show the error.
                    if (statusText == "error" && window.location.protocol == "https:") {
                        // FIXME POSREF this looks like it's dead code.
                        reject({
                            title: _t("HTTPS connection to IoT Box failed"),
                            body: sprintf(
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
        const customerDisplayService = this.globalState.env.services.customer_display;
        if (customerDisplayService) {
            customerDisplayService.update({ closeUI: true });
        }

        // If pos is not properly loaded, we just go back to /web without
        // doing anything in the order data.
        if (!this.globalState || this.globalState.db.get_orders().length === 0) {
            window.location = "/web#action=point_of_sale.action_client_pos_menu";
        }

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
                title: _t("Can't change customer"),
                body: sprintf(
                    _t(
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

    preloadImages() {
        for (const product of this.globalState.db.get_product_by_category(0)) {
            const image = new Image();
            image.src = `/web/image?model=product.product&field=image_128&id=${product.id}&unique=${product.write_date}`;
        }
        for (const category of Object.values(this.globalState.db.category_by_id)) {
            if (category.id == 0) {
                continue;
            }
            const image = new Image();
            image.src = `/web/image?model=pos.category&field=image_128&id=${category.id}&unique=${category.write_date}`;
        }
        const image = new Image();
        image.src = "/point_of_sale/static/src/img/backspace.png";
    }

    /**
     * Close other tabs that contain the same pos session.
     */
    closeOtherTabs() {
        // FIXME POSREF use the bus?
        localStorage["message"] = "";
        localStorage["message"] = JSON.stringify({
            message: "close_tabs",
            session: this.globalState.pos_session.id,
        });

        window.addEventListener(
            "storage",
            (event) => {
                if (event.key === "message" && event.newValue) {
                    const msg = JSON.parse(event.newValue);
                    if (
                        msg.message === "close_tabs" &&
                        msg.session == this.globalState.pos_session.id
                    ) {
                        console.info("POS / Session opened in another window. EXITING POS");
                        this.closePos();
                    }
                }
            },
            false
        );
    }

    showBackButton() {
        return (
            this.mainScreen.component === PaymentScreen ||
            (this.mainScreen.component === ProductScreen && this.globalState.mobile_pane == "left")
        );
    }
}

export const posService = {
    dependencies: PosStore.serviceDependencies,
    async start(env, deps) {
        return new PosStore(env, deps).ready;
    },
};

registry.category("services").add("pos", posService);
