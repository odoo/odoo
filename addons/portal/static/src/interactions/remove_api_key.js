import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { handleCheckIdentity } from './tools';

export class RemoveAPIKey extends Interaction {
    static selector = ".o_portal_remove_api_key";
    dynamicContent = {
        _root: { "t-on-click.prevent": this.onClick },
    };

    async onClick() {
        await this.waitFor(handleCheckIdentity(
            this.services.orm.call("res.users.apikeys", "remove", [parseInt(this.el.id)]),
            this.services.orm,
            this.services.dialog,
        ));
        window.location = window.location;
    }
}

registry
    .category("public.interactions")
    .add("portal.remove_api_key", RemoveAPIKey);
