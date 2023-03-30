/** @odoo-module */

import { useService } from "@web/core/utils/hooks";
import { batched } from "@point_of_sale/js/utils";
import { throttleForAnimation } from "@web/core/utils/timing";
import { Transition } from "@web/core/transition";
import { MainComponentsContainer } from "@web/core/main_components_container";
import { ErrorHandler } from "@web/core/utils/components";
import { Navbar } from "@point_of_sale/app/navbar/navbar";
import { usePos } from "@point_of_sale/app/pos_hook";
import { useExternalListener, useSubEnv, reactive, onWillUnmount, Component } from "@odoo/owl";

/**
 * Chrome is the root component of the PoS App.
 */
export class Chrome extends Component {
    static template = "Chrome"; // FIXME POSREF namespace templates
    static components = { Transition, MainComponentsContainer, ErrorHandler, Navbar };
    setup() {
        this.pos = usePos();
        this.popup = useService("popup");

        const reactivePos = reactive(this.pos.globalState);
        // TODO: Should we continue on exposing posmodel as global variable?
        window.posmodel = reactivePos;
        // FIXME POSREF: remove
        useSubEnv({
            get isMobile() {
                return window.innerWidth <= 768;
            },
            pos: reactive(
                reactivePos,
                batched(() => this.render(true)) // FIXME POSREF remove render(true)
            ),
        });
        let currentIsMobile = this.env.isMobile;
        const updateUI = throttleForAnimation(() => {
            if (this.env.isMobile !== currentIsMobile) {
                currentIsMobile = this.env.isMobile;
                // FIXME POSREF
                this.render(true);
            }
        });
        useExternalListener(window, "resize", updateUI);
        onWillUnmount(updateUI.cancel);

        // prevent backspace from performing a 'back' navigation
        document.addEventListener("keydown", (ev) => {
            if (ev.key === "Backspace" && !ev.target.matches("input, textarea")) {
                ev.preventDefault();
            }
        });

        // This is not done in onWillStart because we want to show the loader immediately
        this.start();
    }
    async start() {
        await this.pos.globalState.load_server_data();
        if (this.pos.globalState.config.use_proxy) {
            await this.pos.connectToProxy();
        }
        this._closeOtherTabs();
        this.pos.uiState = "READY";
        const { name, props } = this.startScreen;
        this.pos.showScreen(name, props);
        this.runBackgroundTasks();
    }

    // GETTERS //

    /**
     * Startup screen can be based on pos config so the startup screen
     * is only determined after pos data is completely loaded.
     */
    get startScreen() {
        return { name: "ProductScreen" };
    }

    // CONTROL METHODS //

    runBackgroundTasks() {
        // push order in the background, no need to await
        this.pos.globalState.push_orders();
        // Allow using the app even if not all the images are loaded.
        // Basically, preload the images in the background.
        this._preloadImages();
        const {
            limited_partners_loading,
            partner_load_background,
            limited_products_loading,
            product_load_background,
        } = this.pos.globalState.config;
        if (limited_partners_loading && partner_load_background) {
            // Wrap in fresh reactive: none of the reads during loading should subscribe to anything
            reactive(this.pos.globalState).loadPartnersBackground();
        }
        if (limited_products_loading && product_load_background) {
            // Wrap in fresh reactive: none of the reads during loading should subscribe to anything
            reactive(this.pos.globalState).loadProductsBackground();
        }
    }

    // MISC METHODS //
    _preloadImages() {
        for (const product of this.pos.globalState.db.get_product_by_category(0)) {
            const image = new Image();
            image.src = `/web/image?model=product.product&field=image_128&id=${product.id}&unique=${product.write_date}`;
        }
        for (const category of Object.values(this.pos.globalState.db.category_by_id)) {
            if (category.id == 0) {
                continue;
            }
            const image = new Image();
            image.src = `/web/image?model=pos.category&field=image_128&id=${category.id}&unique=${category.write_date}`;
        }
        const staticImages = ["backspace.png", "bc-arrow-big.png"];
        for (const imageName of staticImages) {
            const image = new Image();
            image.src = `/point_of_sale/static/src/img/${imageName}`;
        }
    }
    /**
     * Close other tabs that contain the same pos session.
     */
    _closeOtherTabs() {
        // FIXME POSREF use the bus?
        localStorage["message"] = "";
        localStorage["message"] = JSON.stringify({
            message: "close_tabs",
            session: this.pos.globalState.pos_session.id,
        });

        window.addEventListener(
            "storage",
            (event) => {
                if (event.key === "message" && event.newValue) {
                    const msg = JSON.parse(event.newValue);
                    if (
                        msg.message === "close_tabs" &&
                        msg.session == this.pos.globalState.pos_session.id
                    ) {
                        console.info("POS / Session opened in another window. EXITING POS");
                        this.pos.closePos();
                    }
                }
            },
            false
        );
    }
    get showCashMoveButton() {
        return Boolean(this.pos.globalState?.config?.config?.cash_control);
    }
    /**
     * Unmounts the tempScreen on error and dispatches the error in a separate
     * stack so that it can be handled by the error service and display an error
     * popup.
     *
     * @param {any} err the error that was thrown in the temp screen.
     */
    onTempScreenError(err) {
        this.pos.tempScreen = null;
        Promise.reject(err);
    }
}
