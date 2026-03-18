import { ImStatusMixin } from "@mail/core/common/im_status_mixin";
import { fields } from "@mail/model/misc";

import { imageUrl } from "@web/core/utils/urls";

export class ResPartner extends ImStatusMixin {
    static _name = "res.partner";

    /** @type {string} */
    avatar_128_access_token;
    /** @type {string} */
    commercial_company_name;
    country_id = fields.One("res.country");
    /** @type {string} */
    email;
    /**
     * function = job position (Frenchism)
     *
     * @type {string}
     */
    function;
    group_ids = fields.Many("res.groups", { inverse: "partners" });
    /** @type {number} */
    id;
    /** @type {boolean | undefined} */
    is_company;
    /** @type {boolean} */
    is_public;
    main_user_id = fields.One("res.users");
    /** @type {string} */
    name;
    /** @type {string} */
    display_name;
    /** @type {string} */
    phone;
    user_ids = fields.Many("res.users", { inverse: "partner_id" });
    write_date = fields.Datetime();

    get avatarUrl() {
        const accessTokenParam = {};
        if (this.store.self_user?.share !== false) {
            accessTokenParam.access_token = this.avatar_128_access_token;
        }
        return imageUrl("res.partner", this.id, "avatar_128", {
            ...accessTokenParam,
            unique: this.write_date,
        });
    }

    /**
     * ⚠️ This is intentionally a getter and not a field!
     *
     * `store.menuThreads` uses this field to filter threads based on search
     * terms. For each computation, the `menuThread` field is marked as needing a
     * recompute, which can lead to excessive recursion—sometimes even exceeding the
     * call stack size. This computation is simple enough that it doesn’t need a
     * compute and has been replaced by a getter.
     */
    get displayName() {
        return this.name || this.display_name;
    }

    _computeMonitorPresence() {
        return (
            super._computeMonitorPresence() && this.im_status !== "im_partner" && !this.is_public
        );
    }

    searchChat() {
        return Object.values(this.store["discuss.channel"].records).find(
            (channel) =>
                channel.channel_type === "chat" && channel.correspondent?.partner_id?.eq(this)
        );
    }
}

ResPartner.register();
