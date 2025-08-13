import { Component, EventBus, onWillDestroy, onWillStart, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { rpc, RPCError } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
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
        onWillDestroy(() => {
            this.checkIdentity.bus.trigger("stop");
        });
        this.checkIdentity.bus.addEventListener("identityChecked", () => {
            this.close();
        });
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
        this.env.dialogData.dismiss = () => {
            redirect("/web/session/logout");
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

        const run = async () => {
            if (!started) {
                dialog.add(CheckIdentityDialog);
            }
            // Empty the current view, to not let any confidential data displayed
            // not even inspecting the dom or through the console using Javascript.
            env.services.action && env.bus.trigger("ACTION_MANAGER:UPDATE", {});
            await new Promise((resolve) => {
                checkIdentityService.eventBus.addEventListener("identityChecked", resolve, { once: true });
            });
            // Reload the view to display back the data that was displayed before.
            env.services.action && env.services.action.doAction("soft_reload");
        };

        const getInitData = async () => {
            return await rpc("/auth-timeout/session/check-identity");
        };

        bus.addEventListener("start", () => {
            started = true;
        });

        bus.addEventListener("stop", () => {
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
                            // Send the fact the user is away to the server.
                            updatePresence();
                            // Display the check identity dialog
                            await run();
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

        const checkIdentityErrorHandler = (env, error, originalError) => {
            if (originalError instanceof RPCError) {
                if (originalError.data.name === "odoo.addons.auth_timeout.models.ir_http.CheckIdentityException") {
                    run();
                    return true;
                }
            }
        };
        registry.category("error_handlers").add("checkIdentityErrorHandler", checkIdentityErrorHandler);

        return {
            bus,
            check,
            getInitData,
        };
    },
};

registry.category("public_components").add("auth_timeout.check_identity_form", CheckIdentityForm);
registry.category("services").add("check_identity", checkIdentityService);
