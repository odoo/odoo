import { onWillDestroy, Plugin, signal, useListener } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { ConnectionLostError, rpc, rpcBus } from "@web/core/network/rpc";
import { services } from "@web/core/services";

export class OfflinePlugin extends Plugin {
    _timeout = null; // used to repeatedly ping the server when offline

    /** whether the connection to the server is currently lost */
    isOffline = signal(false);

    setup() {
        // Use "offline" and "online" events for instant detection of connection lost/restored.
        useListener(browser, "offline", () => {
            if (!this.isOffline()) {
                this.checkConnection();
            }
        });
        useListener(browser, "online", () => {
            if (this.isOffline()) {
                this.checkConnection();
            }
        });

        // Use RPC:RESPONSE to validate the current offline status, which is more accurate than
        // the "offline"/"online" events (e.g. server is down).
        useListener(rpcBus, "RPC:RESPONSE", (ev) => {
            this.setOffline(ev.detail.error instanceof ConnectionLostError);
        });

        onWillDestroy(() => browser.clearTimeout(this._timeout));
    }

    /**
     * Sets the offline status. While offline, the server is repeatedly pinged to detect if the
     * connection is back.
     *
     * @param {boolean} offline
     */
    setOffline(offline) {
        if (offline === this.isOffline()) {
            return;
        }
        this.isOffline.set(offline);
        if (offline) {
            let delay = 2000;
            const _checkConnection = async () => {
                if (this.isOffline()) {
                    await this.checkConnection();
                    // exponential backoff, with some jitter
                    delay = delay * 1.5 + 500 * Math.random();
                    this._timeout = browser.setTimeout(_checkConnection, delay);
                }
            };
            this._timeout = browser.setTimeout(_checkConnection, delay);
        } else {
            browser.clearTimeout(this._timeout);
        }
    }

    /**
     * Pings the server to check if it is reachable.
     */
    async checkConnection() {
        try {
            await rpc("/web/webclient/version_info", {});
        } catch {
            // just catch the error, the offline status will be updated with RPC:RESPONSE
        }
    }
}

services.add(OfflinePlugin);
