import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { handleCheckIdentity } from "@portal/interactions/portal_security";

export class PortalPasskeyDelete extends Interaction {
    static selector = ".o_passkey_dropdown a[name='delete']";
    dynamicContent = {
        _root: { "t-on-click": this.onClick }
    }

    setup() {
        this.id = parseInt(this.el.parentElement.parentElement.querySelector("input[name='id']").value);
    }

    async onClick() {
        await this.waitFor(handleCheckIdentity(
            this.waitFor(this.services.orm.call("auth.passkey.key", "action_delete_passkey", [this.id])),
            this.services.orm,
            this.services.dialog,
        ));
        location.reload();
    }
}

registry
    .category("public.interactions")
    .add("auth_passkey_portal.delete", PortalPasskeyDelete);
