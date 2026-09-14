/** @odoo-module native */
import { passkeyLib } from "@auth_passkey/passkey_lib";
import {
    guardedByIdentity,
    handleCheckIdentity,
} from "@portal/interactions/portal_security";
import { InputConfirmationDialog } from "@portal/js/components/input_confirmation_dialog/input_confirmation_dialog";
import { makeLogger } from "@web/core/debug/debug_logger";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/translation";
import { user } from "@web/core/user";
import { renderToMarkup } from "@web/core/utils/render";
import { Interaction } from "@web/public/interaction";

const log = makeLogger("portal.passkey");

export class PortalPasskeyCreate extends Interaction {
    static selector = "#portal_passkey_add";
    dynamicContent = {
        _root: { "t-on-click": this.startRegistrationFlow },
    };

    async startRegistrationFlow() {
        return guardedByIdentity(async () => {
            const createAction = await this.waitFor(
                handleCheckIdentity(
                    this.waitFor(
                        this.services.orm.call("res.users", "action_create_passkey", [
                            user.userId,
                        ]),
                    ),
                    this.services.orm,
                    this.services.dialog,
                ),
            );
            const serverOptions = createAction.context.registration;
            this.services.dialog.add(InputConfirmationDialog, {
                title: _t("Create Passkey"),
                body: renderToMarkup("auth_portal.passkey_create"),
                confirmLabel: _t("Create"),
                confirm: async ({ inputEl }) => {
                    const name = inputEl.value;
                    if (name.length > 0) {
                        return guardedByIdentity(() =>
                            this.createPasskey(serverOptions, name),
                        );
                    }
                },
                cancelLabel: _t("Discard"),
                cancel: () => {},
            });
        });
    }

    async createPasskey(serverOptions, name) {
        log.pipeline("request WebAuthn registration");
        const registration = await passkeyLib.startRegistration(serverOptions);
        log.pipeline("create passkey wizard");
        const [wizardId] = await this.waitFor(
            this.services.orm.create("auth.passkey.key.create", [{ name }]),
        );
        await this.waitFor(
            handleCheckIdentity(
                this.waitFor(
                    this.services.orm.call(
                        "auth.passkey.key.create",
                        "action_generate_key",
                        [wizardId, registration],
                    ),
                ),
                this.services.orm,
                this.services.dialog,
            ),
        );
        location.reload();
    }
}

registry
    .category("public.interactions")
    .add("auth_portal.passkey_create", PortalPasskeyCreate);
