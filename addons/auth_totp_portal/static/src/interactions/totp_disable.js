import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { user } from "@web/core/user";

import { handleCheckIdentity } from "@portal/js/portal_security";

export class TOTPDisable extends Interaction {
    static selector = "#auth_totp_portal_disable";
    dynamicContent = {
        _root: { "t-on-click": this.onClick }
    }

    async onClick() {
        await this.waitFor(handleCheckIdentity(
            this.waitFor(this.services.orm.call("res.users", "action_totp_disable", [user.userId])),
            this.services.orm,
            this.services.dialog,
        ));
        location.reload();
    }
}

registry
    .category("public.interactions")
    .add("auth_totp_portal.totp_disable", TOTPDisable);

