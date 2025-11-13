import { Store } from "@mail/core/common/store_service";
import { fields, Record } from "@mail/core/common/record";
import { imageUrl } from "@web/core/utils/urls";
import { debounce } from "@web/core/utils/timing";

const { DateTime } = luxon;

export class ResPartner extends Record {
    static id = "id";
    static _name = "res.partner";
    static new() {
        const record = super.new(...arguments);
        record.debouncedSetImStatus = debounce(
            (newStatus) => record.updateImStatus(newStatus),
            Store.IM_STATUS_DEBOUNCE_DELAY
        );
        return record;
    }

    _triggerPresenceSubscription = fields.Attr(null, {
        compute() {
            return this.monitorPresence && this.presenceChannel;
        },
        onUpdate() {
            if (this.previousPresencechannel) {
                this.store.env.services.bus_service.deleteChannel(this.previousPresencechannel);
            }
            if (this._triggerPresenceSubscription) {
                this.store.env.services.bus_service.addChannel(this.presenceChannel);
            }
            this.previousPresencechannel = this.presenceChannel;
        },
        eager: true,
    });
    /** @type {string} */
    avatar_128_access_token;
    /** @type {string} */
    commercial_company_name;
    country_id = fields.One("res.country");
    debouncedSetImStatus;
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
    /** @type {ImStatus} */
    im_status = fields.Attr(null, {
        onUpdate() {
            if (this.eq(this.store.self_partner) && this.im_status === "offline") {
                this.store.env.services.im_status.updateBusPresence();
            }
        },
    });
    /** @type {string|undefined} */
    im_status_access_token;
    /** @type {boolean | undefined} */
    is_company;
    /** @type {boolean} */
    is_public;
    main_user_id = fields.One("res.users");
    monitorPresence = fields.Attr(false, {
        compute() {
            if (!this.store.env.services.bus_service.isActive || this.id <= 0) {
                return false;
            }
            return this.im_status !== "im_partner" && !this.is_public;
        },
    });
    /** @type {string} */
    name;
    /** @type {string} */
    display_name;
    /** @type {string} */
    phone;
    /** @type {luxon.DateTime} */
    offline_since = fields.Datetime();
    presenceChannel = fields.Attr(null, {
        compute() {
            const channel = `odoo-presence-res.partner_${this.id}`;
            if (this.im_status_access_token) {
                return channel + `-${this.im_status_access_token}`;
            }
            return channel;
        },
    });
    /** @type {string|undefined} */
    previousPresencechannel;
    write_date = fields.Datetime();

    /**
     * @deprecated
     *
     * `store.menuThreads` uses this field to filter threads based on search
     * terms. For each computation, the `menuThread` field is marked as needing a
     * recompute, which can lead to excessive recursion—sometimes even exceeding the
     * call stack size. This computation is simple enough that it doesn’t need a
     * compute and has been replaced by a getter. To override the display name
     * computation, override the displayName getter.
     */
    _computeDisplayName() {
        return this.name || this.display_name;
    }

    get avatarUrl() {
        const accessTokenParam = {};
        if (this.store.self.main_user_id?.share !== false) {
            accessTokenParam.access_token = this.avatar_128_access_token;
        }
        return imageUrl("res.partner", this.id, "avatar_128", {
            ...accessTokenParam,
            unique: this.write_date,
        });
    }

    get displayName() {
        return this._computeDisplayName();
    }

    searchChat() {
        return Object.values(this.store.Thread.records).find(
            (thread) => thread.channel_type === "chat" && thread.correspondent?.persona.eq(this)
        );
    }

    updateImStatus(newStatus) {
        if (newStatus === "offline") {
            this.offline_since = DateTime.now();
        }
        this.im_status = newStatus;
    }
}

ResPartner.register();
