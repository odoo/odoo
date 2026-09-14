/** @odoo-module native */
import {
    guardedByIdentity,
    handleCheckIdentity,
} from "@portal/interactions/portal_security";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { Interaction } from "@web/public/interaction";

export class RevokeAllTrustedDevices extends Interaction {
    static selector = "#auth_portal_revoke_all_devices";
    dynamicContent = {
        _root: { "t-on-click.prevent": this.onClick },
    };

    async onClick() {
        return guardedByIdentity(async () => {
            await this.waitFor(
                handleCheckIdentity(
                    this.waitFor(
                        this.services.orm.call("res.users", "revoke_all_devices", [
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

registry
    .category("public.interactions")
    .add("auth_portal.revoke_all_trusted_devices", RevokeAllTrustedDevices);
