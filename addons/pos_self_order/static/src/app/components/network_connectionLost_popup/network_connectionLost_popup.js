import { Component, onMounted, onWillUnmount, useState } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { ConnectionLostError, rpc } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";

export class NetworkConnectionLostPopup extends Component {
    static template = "pos_self_order.NetworkConnectionLostPopup";
    static props = ["close", "access_token"];

    setup() {
        this.state = useState({
            time: 5,
            online: navigator.onLine,
            retrying: false,
        });

        this.checkConnectivity = this.checkConnectivity.bind(this);
        this.resetTimer = this.resetTimer.bind(this);

        onMounted(() => {
            this.interval = setInterval(() => {
                if (this.state.online) {
                    return;
                }
                if (this.state.retrying) {
                    this.resetTimer();
                } else {
                    this.state.time -= 1;
                    if (this.state.time === 0) {
                        this.state.retrying = true;
                    }
                }
            }, 1000);

            browser.addEventListener("online", this.checkConnectivity);
            browser.addEventListener("offline", this.checkConnectivity);
        });

        onWillUnmount(() => {
            clearInterval(this.interval);
            browser.removeEventListener("online", this.checkConnectivity);
            browser.removeEventListener("offline", this.checkConnectivity);
        });
    }

    resetTimer() {
        this.state.time = 5;
        this.state.retrying = false;
    }

    async checkConnectivity() {
        try {
            clearTimeout(this.checkConnectivityTimeout);
            await rpc("/pos-self/ping", { access_token: this.props.access_token });

            clearInterval(this.interval);
            this.state.online = true;

            this.checkConnectivityTimeout = setTimeout(() => {
                this.props.close();
            }, 2000);
        } catch (error) {
            if (error instanceof ConnectionLostError) {
                this.state.online = false;
                if (navigator.onLine) {
                    this.checkConnectivityTimeout = setTimeout(
                        () => this.checkConnectivity(),
                        2000
                    );
                }
            }
        }
    }
    getRetryText(time) {
        if (time > 1) {
            return _t("Retrying in %s seconds...", time);
        }
        return _t("Retrying in %s second...", time);
    }
}
