import { HWPrinter } from "@point_of_sale/app/printer/hw_printer";
import { EventBus, reactive } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { deduceUrl } from "@point_of_sale/utils";
import { effect } from "@web/core/utils/reactive";

/**
 * This object interfaces with the local proxy to communicate to the various hardware devices
 * connected to the Point of Sale. As the communication only goes from the POS to the proxy,
 * methods are used both to signal an event, and to fetch information. Maybe could be improved
 * by using the bus for two-way communication?
 */
export class HardwareProxy extends EventBus {
    static serviceDependencies = [];
    constructor() {
        super();
        this.setup(...arguments);
    }
    setup() {
        this.host = "";
        this.keptalive = false;
        this.connectionInfo = reactive({ status: "init", drivers: {} });
        effect(
            (info) => {
                if (info.status === "connected" && this.printer) {
                    this.printer.printReceipt();
                }
            },
            [this.connectionInfo]
        );
    }

    setConnectionInfo(info) {
        Object.assign(this.connectionInfo, info);
        if (!info.drivers && this.connectionInfo.status === "disconnected") {
            this.connectionInfo.drivers = {};
        }
    }

    disconnect() {
        if (this.connectionInfo.status !== "disconnected") {
            this.host = null;
            this.setConnectionInfo({ status: "disconnected" });
        }
    }

    async connect() {
        if (this.pos.config.iface_print_via_proxy) {
            this.connectToPrinter();
        }
        try {
            if (await this.message("handshake")) {
                this.setConnectionInfo({ status: "connected" });
                localStorage.hw_proxy_url = this.host;
                this.keepalive();
            } else {
                this.setConnectionInfo({ status: "disconnected" });
                console.error("Connection refused by the Proxy");
            }
        } catch {
            this.setConnectionInfo({ status: "disconnected" });
            console.error("Could not connect to the Proxy");
        }
    }

    connectToPrinter() {
        this.printer = new HWPrinter({ url: this.host });
    }

    /**
     * Find a proxy and connects to it.
     *
     * @param {Object} [options]
     * @param {string} [options.force_ip] only try to connect to the specified ip.
     * @param {string} [options.port]
     * @returns {Promise}
     */
    async autoconnect(options) {
        this.setConnectionInfo({ status: "connecting", drivers: {} });
        let url = options.force_ip || localStorage.hw_proxy_url;
        // Return a pending promise if there is no url to connect to
        // FIXME POSREF do something useful instead if this condition can happen, remove if not
        if (!url) {
            return new Promise(() => {});
        }

        url = deduceUrl(url);

        if (await this.checkProxyAvailability(url)) {
            this.host = url;
            return this.connect(url);
        }
    }

    // starts a loop that updates the connection status
    keepalive() {
        const status = () => {
            const always = () => setTimeout(status, 5000);
            const xhr = new browser.XMLHttpRequest();
            xhr.timeout = 2500;
            rpc(`${this.host}/hw_proxy/status_json`, {}, { silent: true, xhr })
                .then(
                    (drivers) => this.setConnectionInfo({ status: "connected", drivers }),
                    () => {
                        if (this.connectionInfo.status !== "connecting") {
                            this.setConnectionInfo({ status: "disconnected" });
                        }
                    }
                )
                .then(always, always);
        };

        if (!this.keptalive) {
            this.keptalive = true;
            status();
        }
    }

    /**
     * @param {string} name
     * @param {Object} [params]
     * @returns {Promise}
     */
    message(name, params) {
        this.dispatchEvent(new CustomEvent(`send_message:${name}`));
        if (this.connectionInfo.status === "disconnected") {
            return Promise.reject();
        }
        return rpc(`${this.host}/hw_proxy/${name}`, params, { silent: true });
    }

    /**
     * Makes sure that the proxy is available by attempting to call the hello
     * route on the proxy.
     *
     * @param {string} url
     * @returns {Promise<void>}
     */
    async checkProxyAvailability(url) {
        this.setConnectionInfo({ status: "connecting" });
        const maxRetries = 3;
        for (let i = 0; i <= maxRetries; i++) {
            const timeoutController = new AbortController();
            setTimeout(() => timeoutController.abort(), 1000);
            const response = await browser
                .fetch(`${url}/hw_proxy/hello`, {
                    signal: timeoutController.signal,
                })
                .catch(() => ({}));
            if (response.ok) {
                return true;
            }
        }
        this.setConnectionInfo({ status: "disconnected" });
        return false;
    }

    async openCashbox(action = false) {
        if (
            this.pos.config.iface_cashdrawer &&
            this.printer &&
            ["connected", "init"].includes(this.connectionInfo.status)
        ) {
            this.printer.openCashbox();
            if (action) {
                this.pos.logEmployeeMessage(action, "CASH_DRAWER_ACTION");
            }
        }
    }
}

export const hardwareProxyService = {
    dependencies: HardwareProxy.serviceDependencies,
    start(env, deps) {
        return new HardwareProxy(deps);
    },
};

registry.category("services").add("hardware_proxy", hardwareProxyService);
