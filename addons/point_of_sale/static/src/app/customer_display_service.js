/** @odoo-module */

import { batched } from "@point_of_sale/js/utils";
import { effect, Reactive } from "@point_of_sale/utils";
import { registry } from "@web/core/registry";
import { pick } from "@web/core/utils/objects";
import { renderToString } from "@web/core/utils/render";

export class LocalDisplay extends Reactive {
    status = "success";
    constructor() {
        super();
        this.setup(...arguments);
    }
    setup(globalState) {
        this.globalState = globalState;
    }
    async connect() {
        this.popupWindow = window.open("", "Customer Display", "height=600,width=900");
        this.update({ refreshResources: true });
    }
    async update({ refreshResources = false } = {}) {
        if (!this.popupWindow || this.popupWindow.closed) {
            return;
        }
        // TODO: this could probably be improved by loading owl in the popup window,
        // making it render the customer display, and simply sending messages to
        // update the state, instead of sending HTML which causes jankiness with
        // animations.
        const { body: displayBody, head: displayHead } = this.popupWindow.document;
        const container = document.createElement("div");
        container.innerHTML = await this.globalState.customerDisplayHTML();

        if (refreshResources) {
            displayHead.textContent = "";
            displayHead.appendChild(container.querySelector(".resources"));
        }

        displayBody.textContent = "";
        displayBody.appendChild(container.querySelector(".pos-customer_facing_display"));

        const orderLines = displayBody.querySelector(".pos_orderlines_list");
        orderLines.scrollTop = orderLines.scrollHeight;
    }
}

export class RemoteDisplay extends Reactive {
    static serviceDependencies = ["hardware_proxy"];
    status = "failure";
    constructor() {
        super();
        this.setup(...arguments);
    }
    setup(globalState, { hardware_proxy }) {
        this.hardwareProxy = hardware_proxy;
        this.globalState = globalState;
        this.updateStatus();
    }
    async connect() {
        const html = await this.globalState.customerDisplayHTML();
        try {
            const { status } = await this.hardwareProxy.message("take_control", { html });
            this.status = status === "success" ? "success" : "warning";
            this.updateStatus();
        } catch (error) {
            this.status = error === undefined ? "failure" : "not_found";
        }
    }
    async update() {
        const html = await this.globalState.customerDisplayHTML();
        if (this.isUpdatingStatus && this.hardwareProxy.connectionInfo.status === "connected") {
            return this.hardwareProxy.message("customer_facing_display", { html });
        }
    }
    async updateStatus() {
        if (!this.hardwareProxy.host || this.isUpdatingStatus) {
            return;
        }
        this.isUpdatingStatus = true;
        while (this.isUpdatingStatus) {
            try {
                const { status } = await this.hardwareProxy.message("test_ownership");
                this.status = status === "OWNER" ? "success" : "warning";
            } catch (error) {
                if (error === undefined) {
                    // FIXME POSREF when does this happen?
                    this.status = "failure";
                } else {
                    this.status = "not_found";
                    this.isUpdatingStatus = false;
                    return;
                }
            }
            await new Promise((resolve) => setTimeout(resolve, 3000));
        }
    }
}

export const customerDisplayService = {
    get dependencies() {
        // getter so thet the RemoteDisplay dependencies are resolved when services start
        // and not at module definition time, this allows patches to be accounted for
        return ["pos", ...RemoteDisplay.serviceDependencies];
    },
    start(env, deps) {
        const { globalState } = deps.pos;

        const {
            iface_customer_facing_display: enabled,
            iface_customer_facing_display_via_proxy: proxy,
        } = globalState.config;
        if (!enabled) {
            return;
        }

        const display = proxy
            ? new RemoteDisplay(globalState, pick(deps, ...RemoteDisplay.serviceDependencies))
            : new LocalDisplay(globalState);
        // Register an effect to update the display automatically when anything it renders changes
        effect(
            batched((display) => {
                if (renderToString.app) {
                display.update()
                }
            }),
            [display]
        );
        return display;
    },
};

registry.category("services").add("customer_display", customerDisplayService);
