import { Component, EventBus, onWillDestroy, onWillStart, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { rpc, RPCError } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { redirect } from "@web/core/utils/urls";
import { post } from "@web/core/network/http_service";
import { session } from "@web/session";

/**
 * CheckIdentityForm component
 *
 * Displays a re-authentication form based on the user's available authentication methods.
 * Handles form submission, errors and switching methods.
 *
 * @class
 * @extends Component
 * @param {Object} props
 * @param {string} [props.redirect] Optional redirect URL after successful re-authentication
 * @param {Function} [props.close] Callback when the dialog is closed
 */
export class CheckIdentityForm extends Component {
    static template = "web.CheckIdentityForm";
    static props = {
        redirect: { type: String, optional: true },
        close: { type: Function, optional: true },
    };

    async setup() {
        this.authMethodTemplates = {
            password: {
                form: "web.CheckIdentityFormPassword",
                linkString: "web.CheckIdentityLinkStringPassword",
            },
        };

        this.checkIdentityService = useService("check_identity");
        this.checkIdentityService.bus.trigger("start");
        this.state = useState({
            error: false,
            authMethod: null,
        });
        onWillStart(async () => {
            const data = await this.checkIdentityService.getInitData();

            // Attempting to verify the identity of the device using its fingerprint
            if (data.fingerprint_check && await this.checkIdentityService.updateFingerprint()) {
                // There is no need to re-authenticate the user explicitly via the form
                this.checkIdentityService.checkSignaling();
            }

            this.user = {
                userId: data.user_id,
                name: data.login,
            };
            this.setAuthMethods(data.auth_methods);
        });
        onWillDestroy(() => {
            this.checkIdentityService.bus.trigger("stop");
        });
        this.checkIdentityService.bus.addEventListener("identityChecked", () => {
            this.close();
        });
    }

    setAuthMethods(authMethods) {
        this.authMethods = authMethods;
        this.state.authMethod = this.authMethods[0];
    }

    getAuthMethodFormTemplate(authMethod) {
        return this.authMethodTemplates[authMethod].form;
    }

    getAuthMethodLinkStringTemplate(authMethod) {
        return this.authMethodTemplates[authMethod].linkString;
    }

    async onChangeAuthMethod(ev) {
        this.state.authMethod = ev.target.dataset.authMethod;
        this.state.error = false;
    }

    async onSubmit(ev) {
        const form = ev.target;
        const formData = new FormData(form);
        const formValues = Object.fromEntries(formData.entries());
        try {
            const result = await this.checkIdentityService.check(formValues);
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
    static template = "web.CheckIdentityDialog";
    static components = { Dialog, CheckIdentityForm };
    static props = {
        close: Function, // prop added by the Dialog service
    };

    setup() {
        this.formProps = {
            close: this.props.close,
        };
        this.env.dialogData.dismiss = async () => {
            const url = await post('/web/session/logout', { csrf_token: odoo.csrf_token }, "url");
            redirect(url);
        };
    }
}

export class CheckIdentity {

    constructor(env, services) {
        this.env = env;
        this.setup(env, services);
    }

    setup(env, services) {
        this.bus = new EventBus();
        this.channel = new BroadcastChannel("check_identity");
        this.dialogService = services["dialog"];
        this.started = false;
        this.fingerprint = null;

        this.bus.addEventListener("start", () => { this.started = true; });
        this.bus.addEventListener("stop", () => { this.started = false; });
        this.channel.addEventListener("message", (event) => {
            if (event.data === "identityChecked") {
                this.bus.trigger("identityChecked");
            }
        });

        registry.category("error_handlers").add(
            "verifyUserErrorHandler",
            this.verifyUserErrorHandler.bind(this),
            { force: true },
        );

        // Check the fingerprint each time webclient is loaded
        // Only for internal user
        env.bus.addEventListener("WEB_CLIENT_READY", () => {
            if (session.device_salt) {
                this.updateFingerprint()
                    .then(result => !result && this.run())
                    .catch(() => {});
                    // Swallows the error because the goal is to update backend
                    // information. If we have already continued the flow (page
                    // change or other), the request will be closed on the
                    // client side and the error will be `TypeError: Failed to
                    // fetch`. This is a false positive.
            }
        });
    }

    async getFingerprint() {
        if (this.fingerprint) {
            return this.fingerprint;
        }
        // Ask the machine to generate an image (canvas).
        const canvas = new OffscreenCanvas(325, 25);
        const context = canvas.getContext('2d');
        const txt = session.device_salt;
        context.textBaseline = "top";
        context.font = "14px 'Arial'";
        context.textBaseline = "alphabetic";
        const txtWidth = context.measureText(txt).width;
        const txtX = 2;
        const txtY = 15;
        context.fillStyle = "#f60";
        context.fillRect(2 + txtWidth / 2, 1, txtWidth / 2, 20);  // X, Y, width, height
        context.rotate(0.0174533);  // 1 * Math.PI / 180
        context.fillStyle = "rgba(0, 100, 0, 0.6)";
        context.fillText(txt, txtX + 1, txtY + 1);
        context.fillStyle = "#069";
        context.fillText(txt, txtX, txtY);
        const blob = await canvas.convertToBlob();
        const buffer = await blob.arrayBuffer();

        // Hash the canvas image using SHA-256 to generate a unique fingerprint.
        // This prevents canvas forgery.
        let hashBuffer;
        try {
            hashBuffer = await window.crypto.subtle.digest("SHA-256", buffer);
        } catch {
            return this.fingerprint;  // `null` by default
        }

        try {
            this.fingerprint = new Uint8Array(hashBuffer).toBase64();
        } catch {
            // Fallback if `Uint8Array` is not available.
            const uint16array = new Uint16Array(hashBuffer);
            let binary = '';
            for (let i = 0; i < uint16array.length; i++) {
                const value = uint16array[i];
                binary += String.fromCharCode(value & 0xff, value >> 8);
            }
            this.fingerprint = window.btoa(binary);
        }

        return this.fingerprint;
    }

    async getInitData() {
        return await rpc("/web/session/identity/check");
    };

    async updateFingerprint() {
        const fingerprint = await this.getFingerprint();
        if (!fingerprint) return false;

        const response = await fetch("/web/session/fingerprint/check", {
            method: "POST",
            headers: {
                "Content-Type": "application/x-www-form-urlencoded",
            },
            body: new URLSearchParams({ fingerprint: fingerprint }),
        })
        return response.ok;
    }

    async check(credential) {
        const result = await rpc("/web/session/identity/check", credential);
        if (result?.mfa) {
            return { success: false, mfa: result.mfa, auth_methods: result.auth_methods };
        }
        this.checkSignaling();
    };

    checkSignaling() {
        this.bus.trigger("identityChecked");
        this.channel.postMessage("identityChecked");
    }

    async run() {
        if (!this.started) {
            this.dialogService.add(CheckIdentityDialog);
        }
        // Empty the current view, to not let any confidential data displayed
        // not even inspecting the dom or through the console using Javascript.
        this.env.services.action && this.env.bus.trigger("ACTION_MANAGER:UPDATE", {});
        await new Promise((resolve) => {
            this.bus.addEventListener("identityChecked", resolve, { once: true });
        });
        // Reload the view to display back the data that was displayed before.
        if (this.env.services.action) {
            if (this.env.services.action.currentController) {
                this.env.services.action.doAction("soft_reload");
            } else {
                // In the case of multiple concurrent ``CheckIdentityException``
                // managed by differents dispatchers.
                // We get render from HTTP but error from JSONRPC.
                // ``soft_reload`` leaves an empty page.
                // Example: full refresh with an untrusted device.
                this.env.services.action.doAction("reload");
            }
        }
    };

    verifyUserErrorHandler(env, error, originalError) {
        if (originalError instanceof RPCError) {
            if (originalError.data.name === "odoo.http.session.CheckIdentityException") {
                this.run();
                return true;
            }
        }
    };
}

/**
 * Check Identity Service
 *
 * Manages global identity check logic:
 * - Listens for `CheckIdentityException` errors from RPC
 * - Displays dialog and synchronizes re-auth state across tabs
 *
 * @type {Object}
 * @property {string[]} dependencies Service this one relies on: ["dialog"]
 * @method start
 * @param {Object} env OWL environment
 * @param {Object} deps Injected service: dialog
 */
export const checkIdentityService = {
    dependencies: ["dialog"],

    start(env, services) {
        return new CheckIdentity(env, services);
    },
};

registry.category("public_components").add("web.check_identity_form", CheckIdentityForm);
registry.category("services").add("check_identity", checkIdentityService);
