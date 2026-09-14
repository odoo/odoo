/** @odoo-module native */
import {
    guardedByIdentity,
    handleCheckIdentity,
} from "@portal/interactions/portal_security";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { Interaction } from "@web/public/interaction";

export class TOTPDisable extends Interaction {
    static selector = "#auth_portal_totp_disable";
    dynamicContent = {
        _root: { "t-on-click.prevent": this.onClick },
    };

    async onClick() {
        return guardedByIdentity(async () => {
            await this.waitFor(
                handleCheckIdentity(
                    this.waitFor(
                        this.services.orm.call("res.users", "action_totp_disable", [
                            user.userId,
                        ]),
                    ),
                    this.services.orm,
                    this.services.dialog,
                ),
            );
            location.reload();
        });
    }
}

registry.category("public.interactions").add("auth_portal.totp_disable", TOTPDisable);
