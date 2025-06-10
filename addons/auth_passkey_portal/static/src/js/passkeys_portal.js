import { handleCheckIdentity } from "@portal/interactions/portal_security";
import { Interaction } from "@web/public/interaction";
import { InputConfirmationDialog } from "@portal/js/components/input_confirmation_dialog/input_confirmation_dialog";
import { registry } from "@web/core/registry";
import { renderToMarkup } from "@web/core/utils/render";
import { _t } from "@web/core/l10n/translation";

export class PortalPasskey extends Interaction {
    static selector = ".o_passkey_portal_entry";
    dynamicContent = {
        ".o_passkey_portal_rename": {
            "t-on-click": this.onRename,
        },
        ".o_passkey_portal_delete": {
            "t-on-click": this.onDelete,
        },
    };

    setup() {
        this.id = parseInt(this.el.attributes.id.value);
        this.name = this.el.querySelector(".o_passkey_name").innerText;
        this.dropDown = this.el.querySelector(".o_passkey_dropdown");
    }

    async onRename() {
        this.services.dialog.add(InputConfirmationDialog, {
            title: _t("Passkeys"),
            body: renderToMarkup("auth_passkey_portal.rename", { oldname: this.name }),
            confirmLabel: _t("Rename"),
            confirm: async ({ inputEl }) => {
                const name = inputEl.value;
                if (name.length > 0) {
                    await this.services.orm.write("auth.passkey.key", [this.id], { name })
                    location.reload();
                }
            },
            cancelLabel: _t("Discard"),
            cancel: () => {},
        });
    }

    async onDelete() {
        await handleCheckIdentity(
            this.services.orm.call("auth.passkey.key", "action_delete_passkey", [this.id]),
            this.services.orm,
            this.services.dialog
        );
        location.reload();
    }
}

registry.category("public.interactions").add("auth_passkey_portal.passkey", PortalPasskey);
