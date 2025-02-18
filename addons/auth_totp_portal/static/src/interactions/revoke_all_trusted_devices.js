import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { handleCheckIdentity } from "@portal/interactions/portal_security";
import { user } from "@web/core/user";

export class RevokeAllTrustedDevices extends Interaction {
    static selector = "#auth_totp_portal_revoke_all_devices";
    dynamiContent = {
        _root: { "t-on-click.prevent": this.onClick },
    };

    async onClick() {
        await this.waitFor(handleCheckIdentity(
            this.waitFor(this.services.orm.call("res.users", "revoke_all_devices", [user.userId])),
            this.services.orm,
            this.services.dialog,
        ));
        location.reload();
    }
}

registry
    .category("public.interactions")
    .add("auth_totp_portal.revoke_all_trusted_devices", RevokeAllTrustedDevices);
