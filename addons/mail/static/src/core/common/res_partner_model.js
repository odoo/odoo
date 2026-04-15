import { fields, Record } from "@mail/model/export";

import { imageUrl } from "@web/core/utils/urls";

const { DateTime } = luxon;

export class ResPartner extends Record {
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
    /** @type {import("./im_status_mixin").ImStatus} */
    imStatusUI = fields.Attr(undefined, {
        compute() {
            const userStatuses = this.user_ids.map((u) => u.imStatusUI);
            if (userStatuses.includes("online") || this.isBot) {
                return "online";
            } else if (userStatuses.includes("away")) {
                return "away";
            } else if (userStatuses.includes("busy")) {
                return "busy";
            } else if (userStatuses.includes("offline")) {
                return "offline";
            }
        },
    });
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
    /** @type {luxon.DateTime} */
    offline_since = fields.Datetime(undefined, {
        compute: () => DateTime.max(this.user_ids.map((u) => u.offline_since)),
    });
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

    searchChat() {
        return Object.values(this.store["discuss.channel"].records).find(
            (channel) =>
                channel.channel_type === "chat" && channel.correspondent?.partner_id?.eq(this)
        );
    }

    get isBot() {
        return this.eq(this.store.odoobot);
    }
}

ResPartner.register();
