import { Interaction } from "@web/public/interaction";
import { InputConfirmationDialog } from "@portal/js/components/input_confirmation_dialog/input_confirmation_dialog";
import { registry } from "@web/core/registry";
import { renderToMarkup } from "@web/core/utils/render";
import { handleCheckIdentity } from "@portal/interactions/portal_security";
import { _t } from "@web/core/l10n/translation";
import * as passkeyLib from "@auth_passkey/../lib/simplewebauthn";
import { user } from "@web/core/user";

export class PortalPasskeyCreate extends Interaction {
    static selector = "#portal_passkey_add";
    dynamicContent = {
        _root: { "t-on-click": this.startRegistrationFlow },
    };

    async startRegistrationFlow() {
        const create_action = await this.waitFor(
            handleCheckIdentity(
                this.waitFor(
                    this.services.orm.call("res.users", "action_create_passkey", [user.userId])
                ),
                this.services.orm,
                this.services.dialog
            )
        );
        const serverOptions = create_action.context.registration;
        this.services.dialog.add(InputConfirmationDialog, {
            title: _t("Create Passkey"),
            body: renderToMarkup("auth_passkey_portal.create"),
            confirmLabel: _t("Create"),
            confirm: async ({ inputEl }) => {
                const name = inputEl.value;
                if (name.length > 0) {
                    this.createPasskey(serverOptions, name);
                }
            },
            cancelLabel: _t("Discard"),
            cancel: () => {},
        });
    }

    async createPasskey(serverOptions, name) {
        const registration = await passkeyLib
            .startRegistration(serverOptions)
            .catch((e) => console.error(e));
        const [new_key] = await this.services.orm.create("auth.passkey.key.create", [{ name }]);
        await handleCheckIdentity(
            this.services.orm.call("auth.passkey.key.create", "make_key", [
                new_key,
                registration,
            ]),
            this.services.orm,
            this.services.dialog
        );
        location.reload();
    }
}

registry.category("public.interactions").add("auth_passkey_portal.create", PortalPasskeyCreate);
