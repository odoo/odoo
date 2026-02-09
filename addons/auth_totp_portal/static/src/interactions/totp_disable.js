import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";

import { handleCheckIdentity } from "@portal/interactions/portal_security";
import { user } from "@web/core/user";

export class TOTPDisable extends Interaction {
    static selector = "#auth_totp_portal_disable";
    dynamicContent = {
        _root: { "t-on-click.prevent": this.onClick }
    }

    async onClick() {
        this.services.dialog.add(ConfirmationDialog, {
            title: _t("Are you sure?"),
            size: 'md',
            body: _t("If you need to disable 2FA, we recommend re-enabling it as soon as possible."),
            confirmLabel: _t("Yes, Disable 2FA"),
            confirmClass: 'btn-danger',
            confirm: async () => {
                await this.waitFor(handleCheckIdentity(
                    this.waitFor(this.services.orm.call("res.users", "action_totp_disable", [user.userId])),
                    this.services.orm,
                    this.services.dialog,
                ));
                location.reload();
            },
            cancel: () => {},
        });
    }
}

registry
    .category("public.interactions")
    .add("auth_totp_portal.totp_disable", TOTPDisable);

