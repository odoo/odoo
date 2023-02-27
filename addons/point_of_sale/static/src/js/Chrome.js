/** @odoo-module */

import { loadCSS } from "@web/core/assets";
import { useService } from "@web/core/utils/hooks";
import BarcodeParser from "barcodes.BarcodeParser";
import { batched } from "@point_of_sale/js/utils";
import { debounce } from "@web/core/utils/timing";
import { Transition } from "@web/core/transition";
import { MainComponentsContainer } from "@web/core/main_components_container";
import { WithEnv, ErrorHandler } from "@web/core/utils/components";
import { Navbar } from "@point_of_sale/app/navbar/navbar";

// ChromeAdapter imports
import { ProductScreen } from "@point_of_sale/js/Screens/ProductScreen/ProductScreen";
import { registry } from "@web/core/registry";
import { pos_env as env } from "@point_of_sale/js/pos_env";

import { ErrorTracebackPopup } from "./Popups/ErrorTracebackPopup";

import {
    onMounted,
    onWillDestroy,
    useExternalListener,
    useSubEnv,
    reactive,
    onWillUnmount,
    Component,
} from "@odoo/owl";
import { usePos } from "@point_of_sale/app/pos_hook";

/**
 * Chrome is the root component of the PoS App.
 */
export class Chrome extends Component {
    static template = "Chrome"; // FIXME POSREF namespace templates
    static components = { Transition, MainComponentsContainer, WithEnv, ErrorHandler, Navbar };
    setup() {
        this.pos = usePos();
        this.popup = useService("popup");
        // BEGIN ChromeAdapter
        ProductScreen.sortControlButtons();
        const legacyActionManager = useService("legacy_action_manager");

        this.batchedCustomerDisplayRender = batched(() => {
            reactivePos.send_current_order_to_customer_facing_display();
        });
        const reactivePos = reactive(this.pos.globalState, this.batchedCustomerDisplayRender);
        env.pos = reactivePos;
        env.legacyActionManager = legacyActionManager;

        // The proxy requires the instance of PosGlobalState to function properly.
        env.proxy.set_pos(reactivePos);

        // TODO: Should we continue on exposing posmodel as global variable?
        // Expose only the reactive version of `pos` when in debug mode.
        window.posmodel = this.pos.globalState.debug ? reactivePos : this.pos.globalState;

        this.wowlEnv = this.env;
        // FIXME POSREF: make wowl services available in legacy env
        Object.setPrototypeOf(env.services, this.wowlEnv.services);
        this.env = env;
        this.__owl__.childEnv = env;
        useSubEnv({
            get isMobile() {
                return window.innerWidth <= 768;
            },
        });
        let currentIsMobile = this.env.isMobile;
        const updateUI = debounce(() => {
            if (this.env.isMobile !== currentIsMobile) {
                currentIsMobile = this.env.isMobile;
                this.render(true);
            }
        }, 15); // FIXME POSREF use throttleForAnimation?
        useExternalListener(window, "resize", updateUI);
        onWillUnmount(updateUI.cancel);
        // END ChromeAdapter

        super.setup();
        useExternalListener(window, "beforeunload", this._onBeforeUnload);
        useService("number_buffer").activate();

        useSubEnv({
            pos: reactive(
                this.env.pos,
                batched(() => this.render(true)) // FIXME POSREF remove render(true)
            ),
        });

        onMounted(() => {
            // remove default webclient handlers that induce click delay
            // FIXME POSREF if these handlers shouldn't be there we should not load the files that add them.
            $(document).off();
            $(window).off();
            $("html").off();
            $("body").off();
        });

        onWillDestroy(() => {
            try {
                // FIXME POSREF is this needed?
                this.env.pos.destroy();
            } catch {
                // throwing here causes loop
            }
        });

        this.start();
    }

    // GETTERS //

    /**
     * Startup screen can be based on pos config so the startup screen
     * is only determined after pos data is completely loaded.
     *
     * NOTE: Wait for pos data to be completed before calling this getter.
     */
    get startScreen() {
        if (this.pos.uiState !== "READY") {
            console.warn(
                `Accessing startScreen of Chrome component before 'pos.uiState' to be 'READY' is not recommended.`
            );
        }
        return { name: "ProductScreen" };
    }

    // CONTROL METHODS //

    /**
     * Call this function after the Chrome component is mounted.
     * This will load pos and assign it to the environment.
     */
    async start() {
        // Little trick to avoid displaying the block ui during the POS models loading
        // FIXME POSREF: use a silent RPC instead
        const BlockUiFromRegistry = registry.category("main_components").get("BlockUI");
        registry.category("main_components").remove("BlockUI");

        try {
            await this.env.pos.load_server_data();
            await this.setupBarcodeParser();
            if (this.env.pos.config.use_proxy) {
                await this.pos.connect_to_proxy();
            }
            // Load the saved `env.pos.toRefundLines` from localStorage when
            // the PosGlobalState is ready.
            Object.assign(
                this.env.pos.toRefundLines,
                this.env.pos.db.load("TO_REFUND_LINES") || {}
            );
            this._buildChrome();
            this._closeOtherTabs();
            this.env.pos.selectedCategoryId =
                this.env.pos.config.start_category && this.env.pos.config.iface_start_categ_id
                    ? this.env.pos.config.iface_start_categ_id[0]
                    : 0;
            this.pos.uiState = "READY";
            const { name, props } = this.startScreen;
            this.pos.showScreen(name, props);
            setTimeout(() => this._runBackgroundTasks());
        } catch (error) {
            let title = "Unknown Error";
            let body;

            if (error.message && [100, 200, 404, -32098].includes(error.message.code)) {
                // this is the signature of rpc error
                if (error.message.code === -32098) {
                    title = "Network Failure (XmlHttpRequestError)";
                    body =
                        "The Point of Sale could not be loaded due to a network problem.\n" +
                        "Please check your internet connection.";
                } else if (error.message.code === 200) {
                    title = error.message.data.message || this.env._t("Server Error");
                    body =
                        error.message.data.debug ||
                        this.env._t("The server encountered an error while receiving your order.");
                }
            } else if (error instanceof Error) {
                title = error.message;
                if (error.cause) {
                    body = error.cause.message;
                } else {
                    body = error.stack;
                }
            }

            return this.popup.add(ErrorTracebackPopup, { title, body, exitButtonIsShown: true });
        }
        registry.category("main_components").add("BlockUI", BlockUiFromRegistry);

        // Subscribe to the changes in the models.
        this.batchedCustomerDisplayRender();
    }

    _runBackgroundTasks() {
        // push order in the background, no need to await
        this.env.pos.push_orders();
        // Allow using the app even if not all the images are loaded.
        // Basically, preload the images in the background.
        this._preloadImages();
        if (
            this.env.pos.config.limited_partners_loading &&
            this.env.pos.config.partner_load_background
        ) {
            // Wrap in fresh reactive: none of the reads during loading should subscribe to anything
            reactive(this.env.pos).loadPartnersBackground();
        }
        if (
            this.env.pos.config.limited_products_loading &&
            this.env.pos.config.product_load_background
        ) {
            // Wrap in fresh reactive: none of the reads during loading should subscribe to anything
            reactive(this.env.pos)
                .loadProductsBackground()
                .then(() => {
                    this.render(true);
                });
        }
    }

    setupBarcodeParser() {
        if (!this.env.pos.company.nomenclature_id) {
            const errorMessage = this.env._t(
                "The barcode nomenclature setting is not configured. " +
                    "Make sure to configure it on your Point of Sale configuration settings"
            );
            throw new Error(this.env._t("Missing barcode nomenclature"), {
                cause: { message: errorMessage },
            });
        }
        const barcode_parser = new BarcodeParser({
            nomenclature_id: this.env.pos.company.nomenclature_id,
        });
        this.env.barcode_reader.set_barcode_parser(barcode_parser);
        return barcode_parser.is_loaded();
    }

    /**
     * Save `env.pos.toRefundLines` in localStorage on beforeunload - closing the
     * browser, reloading or going to other page.
     */
    _onBeforeUnload() {
        this.env.pos.db.save("TO_REFUND_LINES", this.env.pos.toRefundLines);
    }
    _onSetSyncStatus({ detail: { status, pending } }) {
        this.env.pos.synch.status = status;
        this.env.pos.synch.pending = pending;
    }

    // MISC METHODS //
    _preloadImages() {
        for (const product of this.env.pos.db.get_product_by_category(0)) {
            const image = new Image();
            image.src = `/web/image?model=product.product&field=image_128&id=${product.id}&unique=${product.write_date}`;
        }
        for (const category of Object.values(this.env.pos.db.category_by_id)) {
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

    _buildChrome() {
        if ($.browser.chrome) {
            var chrome_version = $.browser.version.split(".")[0];
            if (parseInt(chrome_version, 10) >= 50) {
                loadCSS("/point_of_sale/static/src/css/chrome50.css");
            }
        }

        if (this.env.pos.config.iface_big_scrollbars) {
            this.pos.hasBigScrollBars = true;
        }

        this._disableBackspaceBack();
    }
    // prevent backspace from performing a 'back' navigation
    _disableBackspaceBack() {
        $(document).on("keydown", function (e) {
            if (e.which === 8 && !$(e.target).is("input, textarea")) {
                e.preventDefault();
            }
        });
    }
    _closeOtherTabs() {
        localStorage["message"] = "";
        localStorage["message"] = JSON.stringify({
            message: "close_tabs",
            session: this.env.pos.pos_session.id,
        });

        window.addEventListener(
            "storage",
            (event) => {
                if (event.key === "message" && event.newValue) {
                    const msg = JSON.parse(event.newValue);
                    if (
                        msg.message === "close_tabs" &&
                        msg.session == this.env.pos.pos_session.id
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
        return this.env.pos && this.env.pos.config && this.env.pos.config.cash_control;
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
