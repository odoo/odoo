import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { handleCheckIdentity } from "@portal/interactions/portal_security";

export class RevokeTrustedDevice extends Interaction {
    static selector = "#totp_wizard_view + * .fa.fa-trash.text-danger";
    dynamiContent = {
        _root: { "t-on-click.prevent": this.onClick },
    };

    async onClick() {
        await this.waitFor(handleCheckIdentity(
            this.waitFor(this.services.orm.call("auth_totp.device", "remove", [parseInt(this.el.id)])),
            this.services.orm,
            this.services.dialog,
        ));
        location.reload();
    }
}

registry
    .category("public.interactions")
    .add("auth_totp_portal.revoke_trusted_device", RevokeTrustedDevice);
