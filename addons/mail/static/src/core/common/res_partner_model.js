import { Store } from "@mail/core/common/store_service";
import { ResPartner } from "@mail/core/common/model_definitions";
import { fields } from "@mail/core/common/record";
import { imageUrl } from "@web/core/utils/urls";
import { debounce } from "@web/core/utils/timing";
import { patch } from "@web/core/utils/patch";

const { DateTime } = luxon;

patch(ResPartner, {
    new() {
        const record = super.new(...arguments);
        record.debouncedSetImStatus = debounce(
            (newStatus) => record.updateImStatus(newStatus),
            Store.IM_STATUS_DEBOUNCE_DELAY
        );
        return record;
    },
});

/** @this {import("models").ResPartner} */
function setup() {
    this._triggerPresenceSubscription = fields.Attr(null, {
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
    this.debouncedSetImStatus;
    this.displayName = fields.Attr(undefined, {
        compute() {
            return this._computeDisplayName();
        },
    });
    this.group_ids = fields.Many("res.groups", { inverse: "partners" });
    this.monitorPresence = fields.Attr(false, {
        compute() {
            if (!this.store.env.services.bus_service.isActive || this.id <= 0) {
                return false;
            }
            return this.im_status !== "im_partner" && !this.is_public;
        },
    });
    this.presenceChannel = fields.Attr(null, {
        compute() {
            const channel = `odoo-presence-res.partner_${this.id}`;
            if (this.im_status_access_token) {
                return channel + `-${this.im_status_access_token}`;
            }
            return channel;
        },
    });
    /** @type {string|undefined} */
    this.previousPresencechannel;
}

patch(ResPartner.prototype, {
    setup() {
        super.setup(...arguments);
        setup.call(this);
    },
    _computeDisplayName() {
        return this.name;
    },
    get avatarUrl() {
        const accessTokenParam = {};
        if (this.store.self_user?.share !== false) {
            accessTokenParam.access_token = this.avatar_128_access_token;
        }
        return imageUrl("res.partner", this.id, "avatar_128", {
            ...accessTokenParam,
            unique: this.write_date,
        });
    },
    searchChat() {
        return Object.values(this.store["mail.thread"].records).find(
            (thread) =>
                thread.channel?.channel_type === "chat" && thread.correspondent?.persona.eq(this)
        );
    },
    updateImStatus(newStatus) {
        if (newStatus === "offline") {
            this.offline_since = DateTime.now();
        }
        this.im_status = newStatus;
    },
    _im_status_onUpdate() {
        if (this.eq(this.store.self_user?.partner_id) && this.im_status === "offline") {
            this.store.env.services.im_status.updateBusPresence();
        }
    },
});
export { ResPartner };
