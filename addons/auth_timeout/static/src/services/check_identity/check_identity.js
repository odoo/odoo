import { Component, EventBus, onWillStart, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { redirect } from "@web/core/utils/urls";
import { session } from "@web/session";

import * as passkeyLib from "@auth_passkey/../lib/simplewebauthn";

/**
 * CheckIdentityForm component
 *
 * Displays a re-authentication form based on the user's available authentication methods.
 * Handles form submission, errors, switching methods, and passkey (WebAuthn) flows.
 *
 * @class
 * @extends Component
 * @param {Object} props
 * @param {string} [props.redirect] Optional redirect URL after successful re-authentication
 * @param {Function} [props.close] Callback when the dialog is closed
 */
export class CheckIdentityForm extends Component {
    static template = "auth_timeout.CheckIdentityForm";
    static props = {
        redirect: { type: String, optional: true },
        close: { type: Function, optional: true },
    };
    static authMethodTemplates = {
        password: {
            form: "auth_timeout.CheckIdentityFormPassword",
            linkString: "auth_timeout.CheckIdentityLinkStringPassword",
        },
        totp: {
            form: "auth_timeout.CheckIdentityFormTOTP",
            linkString: "auth_timeout.CheckIdentityLinkStringTOTP",
        },
        totp_mail: {
            form: "auth_timeout.CheckIdentityFormTOTPMail",
            linkString: "auth_timeout.CheckIdentityLinkStringTOTPMail",
        },
        webauthn: {
            form: "auth_timeout.CheckIdentityFormWebAuthN",
            linkString: "auth_timeout.CheckIdentityLinkStringWebAuthN",
        },
    };

    async setup() {
        super.setup();
        this.checkIdentity = useService("check_identity");
        this.checkIdentity.bus.trigger("start");
        this.state = useState({
            error: false,
            authMethod: null,
        });
        onWillStart(async () => {
            const data = await this.checkIdentity.getInitData();
            this.user = {
                userId: data.user_id,
                name: data.login,
            };
            this.setAuthMethods(data.auth_methods);
        });
        this.checkIdentity.bus.addEventListener("identityChecked", () => {
            this.success = true;
            this.close();
        });
        this.env.dialogData.dismiss = this.dismiss.bind(this);
    }

    async dismiss() {
        redirect("/web/session/logout");
    }

    setAuthMethods(authMethods) {
        this.authMethods = authMethods;
        this.state.authMethod = this.authMethods[0];
    }

    getAuthMethodFormTemplate(authMethod) {
        return CheckIdentityForm.authMethodTemplates[authMethod].form;
    }

    getAuthMethodLinkStringTemplate(authMethod) {
        return CheckIdentityForm.authMethodTemplates[authMethod].linkString;
    }

    async onSubmit(ev) {
        const form = ev.target;
        if (form.querySelector('input[name="type"]').value === "webauthn") {
            const serverOptions = await rpc("/auth/passkey/start-auth");
            const auth = await passkeyLib.startAuthentication(serverOptions).catch((e) => console.log(e));
            if (!auth) {
                return false;
            }
            form.querySelector('input[name="webauthn_response"]').value = JSON.stringify(auth);
        }
        const formData = new FormData(form);
        const formValues = Object.fromEntries(formData.entries());
        try {
            const result = await this.checkIdentity.check(formValues);
            if (result?.mfa) {
                this.setAuthMethods(result.auth_methods);
            }
        } catch (error) {
            if (error.data) {
                this.state.error = error.data.message;
            } else {
                this.state.error = "Your identity could not be confirmed";
            }
        }
    }

    close() {
        if (this.props.close) {
            this.props.close();
        }
        if (this.props.redirect) {
            redirect(this.props.redirect);
        }
    }

    async onChangeAuthMethod(ev) {
        this.state.authMethod = ev.target.dataset.authMethod;
        this.state.error = false;
        if (this.state.authMethod == "totp_mail") {
            try {
                await rpc("/auth-timeout/send-totp-mail-code");
            } catch (error) {
                if (error.data) {
                    this.state.error = error.data.message;
                } else {
                    this.state.error = "The code could not be sent by email";
                }
            }
        }
    }
}

/**
 * CheckIdentityDialog component
 *
 * Wraps CheckIdentityForm in a modal dialog, used by the check_identity service.
 *
 * @class
 * @extends Component
 * @param {Object} props
 * @param {Function} props.close Callback passed by the Dialog service to close the modal
 */
export class CheckIdentityDialog extends Component {
    static template = "auth_timeout.CheckIdentityDialog";
    static components = { Dialog, CheckIdentityForm };
    static props = {
        close: Function, // prop added by the Dialog service
    };

    setup() {
        this.formProps = {
            close: this.props.close,
        };
    }
}

/**
 * Check Identity Service
 *
 * Manages global identity check logic:
 * - Listens for inactivity via presence service
 * - Listens for `CheckIdentityException` errors from RPC
 * - Displays dialog and synchronizes re-auth state across tabs
 *
 * @type {Object}
 * @property {string[]} dependencies Services this one relies on: ["bus_service", "dialog", "presence"]
 * @method start
 * @param {Object} env OWL environment
 * @param {Object} deps Injected services: bus_service, dialog, presence
 * @returns {Object} Service interface with {channel, bus, run}
 */
export const checkIdentityService = {
    dependencies: ["bus_service", "dialog", "presence"],
    eventBus: new EventBus(),
    /**
     * Runs the identity check dialog if not already shown.
     *
     * Used by patched RPC calls and inactivity timers to ensure
     * identity confirmation is enforced only once at a time.
     *
     * @returns {Promise<void>} Resolves when the user completes the check.
     */
    run() {
        this.eventBus.trigger("run");
        return new Promise((resolve) => {
            checkIdentityService.eventBus.addEventListener("identityChecked", resolve, { once: true });
        });
    },
    start(env, { bus_service, dialog, presence }) {
        const channel = new BroadcastChannel("check_identity");
        const bus = this.eventBus;
        let started = false;
        let inactivityTimer;

        const check = async (credential) => {
            const result = await rpc("/auth-timeout/session/check-identity", credential);
            if (result?.mfa) {
                return { success: false, mfa: result.mfa, auth_methods: result.auth_methods };
            }
            bus.trigger("identityChecked");
            channel.postMessage("identityChecked");
        };

        const getInitData = async () => {
            return await rpc("/auth-timeout/session/check-identity");
        };

        bus.addEventListener("run", () => {
            if (!started) {
                dialog.add(CheckIdentityDialog);
            }
        });

        bus.addEventListener("start", () => {
            started = true;
        });

        bus.addEventListener("identityChecked", () => {
            started = false;
        });

        channel.addEventListener("message", (event) => {
            if (event.data === "identityChecked") {
                bus.trigger("identityChecked");
            }
        });

        // Inactivity: Set a timer after which the check identity automatically appear.
        if (session.lock_timeout_inactivity) {
            // Start the bus to be able to send inactivities / presences
            bus_service.start();
            const updatePresence = () => {
                bus_service.send("update_presence", { inactivity_period: presence.getInactivityPeriod() });
            };
            // Immediately send a presence on bus connect
            bus_service.addEventListener("connect", () => updatePresence(), { once: true });
            const startInactivityTimer = () => {
                inactivityTimer = setTimeout(
                    async () => {
                        if (presence.getInactivityPeriod() >= session.lock_timeout_inactivity * 1000) {
                            // Empty the current view, to not let any confidential data displayed
                            // not even inspecting the dom or through the console using Javascript.
                            env.services.action && env.bus.trigger("ACTION_MANAGER:UPDATE", {});
                            // Send the fact the user is away to the server.
                            updatePresence();
                            // Display the check identity dialog
                            await this.run();
                            // Reload the view to display back the data that was displayed before.
                            env.services.action && env.services.action.doAction("soft_reload");
                        }
                        startInactivityTimer();
                    },
                    session.lock_timeout_inactivity * 1000 - presence.getInactivityPeriod(),
                );
            };

            presence.bus.addEventListener("presence", () => {
                if (!started) {
                    clearTimeout(inactivityTimer);
                    startInactivityTimer();
                }
            });

            startInactivityTimer();
        }

        return {
            bus,
            check,
            getInitData,
        };
    },
};

/**
 * @override
 * Override the core RPC method to catch CheckIdentityException.
 *
 * If such an exception is caught, the identity check dialog is triggered,
 * and the original request is retried after successful re-authentication.
 *
 * @function
 * @param {string} url The RPC endpoint
 * @param {Object} params The RPC parameters
 * @param {Object} settings Additional request settings
 * @returns {Promise<any>} A promise resolving to the RPC result
 */
patch(rpc, {
    _rpc(url, params, settings) {
        // `rpc._rpc` returns a promise with an additional attribute `.abort`
        // It needs to be forwarded to the new promise as some feature requires it.
        // e.g.
        // `record_autocomplete.js`
        // ```js
        // if (this.lastProm) {
        //     this.lastProm.abort(false);
        // }
        // this.lastProm = this.search(name, SEARCH_LIMIT + 1);
        // ```
        // --test-tags /account_reports.test_tour_account_report_analytic_filters
        // --test-tags /web_studio.test_rename
        const originPromise = super._rpc(url, params, settings);
        const promise = originPromise.catch(async (error) => {
            if (error.data && error.data.name === "odoo.addons.auth_timeout.models.ir_http.CheckIdentityException") {
                await checkIdentityService.run();
                const newPromise = rpc._rpc(url, params, settings);
                promise.abort = newPromise.abort;
                return newPromise;
            }
            throw error;
        });
        promise.abort = originPromise.abort;
        return promise;
    },
});

registry.category("public_components").add("auth_timeout.check_identity_form", CheckIdentityForm);
registry.category("services").add("check_identity", checkIdentityService);
