/** @odoo-module */

import { batched } from "@web/core/utils/timing";
import { registry } from "@web/core/registry";
import { pick } from "@web/core/utils/objects";
import { Reactive, effect } from "@web/core/utils/reactive";

export class LocalDisplay extends Reactive {
    status = "success";
    constructor() {
        super();
        this.setup(...arguments);
    }
    setup(pos) {
        this.pos = pos;
    }
    async connect() {
        if (this.popupWindow && !this.popupWindow.closed) {
            return;
        }

        // Because there is no way to know if the popup is already opened, PopupWindowLastStatus
        // localStorage boolean is used to know if the popup was opened.
        // This allows to get the already opened popup, and prevents to open the customer display
        // automatically by default (most web browsers forbid to open popup windows without an user
        // interaction, like a button click).
        // window.open will get the already opened popup or otherwise open one
        this.popupWindow = window.open("", "Customer Display", "height=600,width=900");
        if (this.popupWindow && !this.popupWindow.closed) {
            this.setPopupWindowLastStatus(true);
            this.popupWindow.addEventListener("beforeunload", () => {
                this.setPopupWindowLastStatus(false);
            });
            this.update({ refreshResources: true });
        } else {
            this.setPopupWindowLastStatus(false);
        }
    }
    setPopupWindowLastStatus(open) {
        if (open) {
            window.localStorage.setItem("pos-customerdisplay-local-open", "true");
        } else {
            window.localStorage.removeItem("pos-customerdisplay-local-open");
        }
    }
    isPopupWindowLastStatusOpen() {
        return window.localStorage.getItem("pos-customerdisplay-local-open") === "true";
    }
    async update({ refreshResources = false, closeUI = false } = {}) {
        if (!this.popupWindow || this.popupWindow.closed) {
            if (this.isPopupWindowLastStatusOpen()) {
                this.connect();
            }
            return;
        }
        // TODO: this could probably be improved by loading owl in the popup window,
        // making it render the customer display, and simply sending messages to
        // update the state, instead of sending HTML which causes jankiness with
        // animations.
        const { body: displayBody, head: displayHead } = this.popupWindow.document;
        const container = document.createElement("div");
        container.innerHTML = await this.pos.customerDisplayHTML(closeUI);

        if (!container.innerHTML || container.innerHTML === "undefined") {
            displayBody.textContent = "";
            return;
        }

        if (displayHead.innerHTML.trim().length == 0 || refreshResources) {
            displayHead.textContent = "";
            displayHead.appendChild(container.querySelector(".resources"));
            // The scripts must be evaluated because adding an element containing
            // a script block doesn't make it evaluated.
            const scriptContent = displayHead.querySelector(
                "script#old_browser_fix_auto_scroll"
            ).innerHTML;
            this.popupWindow.eval(scriptContent);
        }

        displayBody.textContent = "";
        displayBody.appendChild(container.querySelector(".pos-customer_facing_display"));

        // The fixScrollingIfNecessary method is called in setTimeout to be called after
        // the old_browser_fix_auto_scroll script is evaluated and after the body is updated.
        setTimeout(() => {
            this.popupWindow.fixScrollingIfNecessary();
        }, 0);
    }
}

export class RemoteDisplay extends Reactive {
    static serviceDependencies = ["hardware_proxy"];
    status = "failure";
    constructor() {
        super();
        this.setup(...arguments);
    }
    setup(pos, { hardware_proxy }) {
        this.hardwareProxy = hardware_proxy;
        this.pos = pos;
        this.updateStatus();
    }
    async connect() {
        const html = await this.pos.customerDisplayHTML();
        try {
            const { status } = await this.hardwareProxy.message("take_control", { html });
            this.status = status === "success" ? "success" : "warning";
            this.updateStatus();
        } catch (error) {
            this.status = error === undefined ? "failure" : "not_found";
        }
    }
    async update({ closeUI = false } = {}) {
        const html = await this.pos.customerDisplayHTML(closeUI);
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
        const pos = deps.pos;

        const {
            iface_customer_facing_display: enabled,
            iface_customer_facing_display_via_proxy: proxy,
        } = pos.config;
        if (!enabled) {
            return;
        }

        const display = proxy
            ? new RemoteDisplay(pos, pick(deps, ...RemoteDisplay.serviceDependencies))
            : new LocalDisplay(pos);
        // Register an effect to update the display automatically when anything it renders changes
        effect(
            batched((display) => display.update()),
            [display]
        );
        return display;
    },
};

registry.category("services").add("customer_display", customerDisplayService);
