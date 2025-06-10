import { Interaction } from "@web/public/interaction";
import { InputConfirmationDialog } from "@portal/js/components/input_confirmation_dialog/input_confirmation_dialog";
import { registry } from "@web/core/registry";
import { renderToMarkup } from "@web/core/utils/render";
import { _t } from "@web/core/l10n/translation";

export class PortalPasskeyRename extends Interaction {
    static selector = ".o_passkey_dropdown a[name='rename']";
    dynamicContent = {
        _root: { "t-on-click": this.onClick }
    }

    setup() {
        this.id = parseInt(this.el.parentElement.parentElement.querySelector("input[name='id']").value);
        this.name = this.el.parentElement.parentElement.querySelector('.o_passkey_name').innerText;
    }

    async onClick() {
        this.services.dialog.add(InputConfirmationDialog, {
            title: _t("Passkeys"),
            body: renderToMarkup("auth_passkey_portal.rename", {oldname: this.name}),
            confirmLabel: _t("Rename"),
            confirm: async ({ inputEl }) => {
                const name = inputEl.value;
                if(name.length > 0) {
                    await this.waitFor(this.services.orm.write("auth.passkey.key", [this.id], { name }));
                    location.reload();
                }
            },
            cancelLabel: _t("Discard"),
            cancel: () => {},
        });
    }
}

registry
    .category("public.interactions")
    .add("auth_passkey_portal.rename", PortalPasskeyRename);
