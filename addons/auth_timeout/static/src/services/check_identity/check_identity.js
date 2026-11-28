import { BusPlugin } from "@bus/services/bus_plugin";
import { PresencePlugin } from "@bus/services/presence_plugin";
import { onWillDestroy, Plugin, useListener, usePlugin, useScope } from "@odoo/owl";
import { services } from "@web/core/services";
import { CheckIdentityPlugin } from "@web/core/session/check_identity";
import { session } from "@web/session";

export class CheckIdentityTimeoutPlugin extends Plugin {
    #scope = useScope();

    #checkIdentityPlugin = usePlugin(CheckIdentityPlugin);
    #busPlugin = usePlugin(BusPlugin);
    #presencePlugin = usePlugin(PresencePlugin);

    #inactivityTimer = 0;

    setup() {
        // Inactivity: Set a timer after which the check identity automatically appear.
        if (session.lock_timeout_inactivity) {
            // Start the bus to be able to send inactivities / presences
            this.#busPlugin.start();
            this.updatePresence();
            // A closed socket sets the next identity check: send a presence on each (re)connection.
            useListener(this.#busPlugin, "BUS:CONNECT", () => this.updatePresence());
            useListener(this.#busPlugin, "BUS:RECONNECT", () => this.updatePresence());
            useListener(this.#presencePlugin.bus, "presence", () => {
                if (!this.#checkIdentityPlugin.isCheckingIdentity) {
                    clearTimeout(this.#inactivityTimer);
                    this.startInactivityTimer();
                }
            });

            this.startInactivityTimer();
        }

        onWillDestroy(() => {
            clearTimeout(this.#inactivityTimer);
        });
    }

    updatePresence() {
        this.#busPlugin.send("update_presence",
            { inactivity_period: this.#presencePlugin.getInactivityPeriod() }
        );
    }

    startInactivityTimer() {
        this.#inactivityTimer = setTimeout(
            async () => {
                if (this.#scope.isDestroyed()) {
                    return;
                }
                if (this.#presencePlugin.getInactivityPeriod() >= session.lock_timeout_inactivity * 1000) {
                    // Send the fact the user is away to the server.
                    this.updatePresence();
                    // Display the check identity dialog
                    await this.#checkIdentityPlugin.run();
                }
                this.startInactivityTimer();
            },
            session.lock_timeout_inactivity * 1000 - this.#presencePlugin.getInactivityPeriod(),
        );
    }

}
services.add(CheckIdentityTimeoutPlugin);
