import { Component, onWillStart, onWillUnmount, signal } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { rpc } from "@web/core/network/rpc";
import { session } from "@web/session";

const POLL_STATUS_MS = session.test_mode ? 100 : 5000;
const RETRY_ON_ERROR_MS = session.test_mode ? 200 : 30000;

export class PairingPage extends Component {
    static template = "pos_self_order.PairingIndex";

    pairingData = signal();
    error = signal(null);

    async setup() {
        onWillStart(() => {
            this.requestPairing();
        });

        onWillUnmount(() => {
            if (this.pollTimeout) {
                browser.clearTimeout(this.pollTimeout);
            }
            if (this.statusInterval) {
                clearInterval(this.statusInterval);
            }
        });
    }

    get formattedCodeGroups() {
        const data = this.pairingData();
        if (!data) {
            return "";
        }
        const code = data.pairing_code.replace(/\s+/g, "") || "";
        return code.match(/\d{1,3}(?=(\d{3})*$)/g) || [];
    }

    async requestPairing() {
        try {
            const params = await this.getPairingExtraParameters();

            const res = await rpc("/pos-self-kiosk/pairing/" + odoo.pos_config_id, {
                access_token: odoo.access_token,
                ...params,
            });
            if (res.already_paired) {
                window.location.reload();
                return;
            }
            this.error.set(null);
            this.pairingData.set(res);
            this.startStatusPolling();
        } catch (e) {
            console.error(e);
            this.pairingData.set(null);
            const isUserError = e.data?.name === "odoo.exceptions.UserError";
            this.error.set((isUserError && e.data?.message) || e.message);
            this.scheduleRetryPairing(RETRY_ON_ERROR_MS);
        }
    }

    async getPairingExtraParameters() {
        return {};
    }

    scheduleRetryPairing(delay = POLL_STATUS_MS) {
        this.pollTimeout = browser.setTimeout(() => this.requestPairing(), delay);
    }

    startStatusPolling() {
        this.statusInterval = setInterval(async () => {
            try {
                const data = await rpc(
                    "/pos-self-kiosk/pairing/" + odoo.pos_config_id + "/status",
                    {
                        access_token: odoo.access_token,
                    }
                );

                if (data.status === "approved") {
                    clearInterval(this.statusInterval);
                    window.location.reload();
                } else if ("invalid".includes(data.status)) {
                    clearInterval(this.statusInterval);
                    this.pairingData.set(null);
                    this.requestPairing();
                }
            } catch (e) {
                console.warn("Pairing poll failed, will retry", e);
            }
        }, POLL_STATUS_MS);
    }
}
