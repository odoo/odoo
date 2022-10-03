/** @odoo-module */

import Chrome from "point_of_sale.Chrome";
import ProductScreen from "point_of_sale.ProductScreen";
import Registries from "point_of_sale.Registries";
import { PosGlobalState } from "point_of_sale.models";
import { configureGui } from "point_of_sale.Gui";
import { registry } from "@web/core/registry";
import { debounce } from "@web/core/utils/timing";
import { batched } from "point_of_sale.utils";

import concurrency from 'web.concurrency';
import devices from 'point_of_sale.devices';
import BarcodeReader from 'point_of_sale.BarcodeReader';

const { Component, reactive, markRaw, useExternalListener, onWillUnmount, xml } = owl;

export class ChromeAdapter extends Component {
    setup() {
        this.PosChrome = Registries.Component.get(Chrome);
        ProductScreen.sortControlButtons();

        // Augment the default env.
        const pos_env = Object.assign(Object.create(this.env), {
            get isMobile() {
                return window.innerWidth <= 768;
            },
            isDebug() {
                return this.debug;
            },
        });
        pos_env.proxy_queue = new devices.JobQueue(); // used to prevent parallels communications to the proxy
        pos_env.proxy = new devices.ProxyDevice({ env: pos_env }); // used to communicate to the hardware devices via a local proxy
        pos_env.barcode_reader = new BarcodeReader({ env: pos_env, proxy: pos_env.proxy });
        pos_env.posbus = new owl.EventBus();
        pos_env.posMutex = new concurrency.Mutex();

        // Instantiate PosGlobalState here to ensure that every extension
        // (or class overloads) is taken into consideration.
        const pos = PosGlobalState.create(markRaw(pos_env));

        this.batchedCustomerDisplayRender = batched(() => {
            reactivePos.send_current_order_to_customer_facing_display();
        });
        const reactivePos = reactive(pos, this.batchedCustomerDisplayRender);
        pos_env.pos = reactivePos;

        // The proxy requires the instance of PosGlobalState to function properly.
        pos_env.proxy.set_pos(reactivePos);

        // TODO: Should we continue on exposing posmodel as global variable?
        // Expose only the reactive version of `pos` when in debug mode.
        window.posmodel = pos.debug ? reactivePos : pos;

        this.env = pos_env;
        this.__owl__.childEnv = pos_env;

        let currentIsMobile = this.env.isMobile;
        const updateUI = debounce(() => {
            if (this.env.isMobile !== currentIsMobile) {
                currentIsMobile = this.env.isMobile;
                this.render(true);
            }
        }, 15);
        useExternalListener(window, "resize", updateUI);
        onWillUnmount(updateUI.cancel);
    }

    async configureAndStart(chrome) {
        // Add the pos error handler when the chrome component is available.
        registry.category('error_handlers').add(
            'posErrorHandler',
            (env, ...noEnvArgs) => {
                if (chrome) {
                    return chrome.errorHandler(this.env, ...noEnvArgs);
                }
                return false;
            },
            { sequence: 0 }
        );
        // Little trick to avoid displaying the block ui during the POS models loading
        const BlockUiFromRegistry = registry.category("main_components").get("BlockUI");
        registry.category("main_components").remove("BlockUI");
        configureGui({ component: chrome });
        await chrome.start();
        registry.category("main_components").add("BlockUI", BlockUiFromRegistry);

        // Subscribe to the changes in the models.
        this.batchedCustomerDisplayRender();
    }
}
ChromeAdapter.template = xml`<t t-component="PosChrome" setupIsDone.bind="configureAndStart"/>`;
