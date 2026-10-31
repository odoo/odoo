import { BusPlugin } from "@bus/services/bus_plugin";
import { PresencePlugin } from "@bus/services/presence_plugin";
import { onWillDestroy, Plugin, useListener, usePlugin, useScope } from "@odoo/owl";
import { services } from "@web/core/services";
import { CheckIdentityPlugin } from "@web/core/session/check_identity";
import { session } from "@web/session";

export class CheckIdentityTimeoutPlugin extends Plugin {
    /** @private */
    scope = useScope();

    /** @private */
    checkIdentityPlugin = usePlugin(CheckIdentityPlugin);
    /** @private */
    busPlugin = usePlugin(BusPlugin);
    /** @private */
    presencePlugin = usePlugin(PresencePlugin);

    /** @private */
    inactivityTimer = 0;

    setup() {
        // Inactivity: Set a timer after which the check identity automatically appear.
        if (session.lock_timeout_inactivity) {
            const onBusConnected = () => {
                this.updatePresence();
                this.busPlugin.removeEventListener("connect", onBusConnected);
            };
            // Immediately send a presence on bus connect
            this.busPlugin.addEventListener("connect", onBusConnected);
            onWillDestroy(() => {
                this.busPlugin.removeEventListener("connect", onBusConnected);
            });

            // Start the bus to be able to send inactivities / presences
            this.busPlugin.start();
            this.updatePresence();

            useListener(this.presencePlugin.bus, "presence", () => {
                if (!this.checkIdentityPlugin.identityCheckPromise) {
                    clearTimeout(this.inactivityTimer);
                    this.startInactivityTimer();
                }
            });

            this.startInactivityTimer();
        }

        onWillDestroy(() => {
            clearTimeout(this.inactivityTimer);
        });
    }

    updatePresence() {
        this.busPlugin.send("update_presence",
            { inactivity_period: this.presencePlugin.getInactivityPeriod() }
        );
    }

    startInactivityTimer() {
        this.inactivityTimer = setTimeout(
            async () => {
                if (this.scope.isDestroyed()) {
                    return;
                }
                if (this.presencePlugin.getInactivityPeriod() >= session.lock_timeout_inactivity * 1000) {
                    // Send the fact the user is away to the server.
                    this.updatePresence();
                    // Display the check identity dialog
                    await this.checkIdentityPlugin.run();
                }
                this.startInactivityTimer();
            },
            session.lock_timeout_inactivity * 1000 - this.presencePlugin.getInactivityPeriod(),
        );
    }

}
services.add(CheckIdentityTimeoutPlugin);
