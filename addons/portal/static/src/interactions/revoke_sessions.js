import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { user } from "@web/core/user";

import { handleCheckIdentity } from './tools';

export class RevokeSessions extends Interaction {
    static selector = "#portal_revoke_all_sessions_popup";
    dynamicContent = {
        _root: { "t-on-click": this.onClick },
    };

    async onClick() {
        await this.waitFor(handleCheckIdentity(
            this.services.orm.call("res.users", "action_revoke_all_devices", [user.userId]),
            this.services.orm,
            this.services.dialog,
        ));
        window.location = window.location;
    }
}

registry
    .category("public.interactions")
    .add("portal.revoke_sessions", RevokeSessions);
