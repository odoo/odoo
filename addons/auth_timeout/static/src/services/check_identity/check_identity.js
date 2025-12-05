import { registry } from "@web/core/registry";
import { session } from "@web/session";

export class CheckIdentityTimeout {

    constructor(env, services) {
        this.env = env;
        this.setup(env, services);
    }

    setup(env, services) {
        this.checkIdentityService = services["check_identity"];
        this.busService = services["bus_service"];
        this.presenceService = services["presence"];
        this.inactivityTimer;

        // Inactivity: Set a timer after which the check identity automatically appear.
        if (session.lock_timeout_inactivity) {
            // Start the bus to be able to send inactivities / presences
            this.busService.start();
            this.updatePresence();
            // Immediately send a presence on bus connect
            this.busService.addEventListener("connect", () => this.updatePresence(), { once: true });

            this.presenceService.bus.addEventListener("presence", () => {
                if (!this.checkIdentityService.started) {
                    clearTimeout(this.inactivityTimer);
                    this.startInactivityTimer();
                }
            });

            this.startInactivityTimer();
        }
    }

    updatePresence() {
        this.busService.send("update_presence",
            { inactivity_period: this.presenceService.getInactivityPeriod() }
        );
    }

    startInactivityTimer() {
        this.inactivityTimer = setTimeout(
            async () => {
                if (this.presenceService.getInactivityPeriod() >= session.lock_timeout_inactivity * 1000) {
                    // Send the fact the user is away to the server.
                    this.updatePresence();
                    // Display the check identity dialog
                    await this.checkIdentityService.run();
                }
                this.startInactivityTimer();
            },
            session.lock_timeout_inactivity * 1000 - this.presenceService.getInactivityPeriod(),
        );
    }

}

/**
 * Check Identity TimeoutService
 *
 * Manages global identity check logic:
 * - Listens for inactivity via presence service
 *
 * @type {Object}
 * @property {string[]} dependencies Services this one relies on: ["check_identity", "bus_service", "presence"]
 * @method start
 * @param {Object} env OWL environment
 * @param {Object} deps Injected services: check_identity, bus_service, presence
 */
export const checkIdentityTimeoutService = {
    dependencies: ["check_identity", "bus_service", "presence"],

    start(env, services) {
        return new CheckIdentityTimeout(env, services);
    },
};

registry.category("services").add("check_identity_timeout", checkIdentityTimeoutService);
