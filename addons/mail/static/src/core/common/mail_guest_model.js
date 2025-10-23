import { fields } from "@mail/core/common/record";
import { MailGuest } from "@mail/core/common/model_definitions";
import { imageUrl } from "@web/core/utils/urls";
import { rpc } from "@web/core/network/rpc";
import { debounce } from "@web/core/utils/timing";
import { Store } from "@mail/core/common/store_service";
import { patch } from "@web/core/utils/patch";

const TRANSPARENT_AVATAR =
    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAIAAAACACAQAAABpN6lAAAAAqElEQVR42u3QMQEAAAwCoNm/9GJ4CBHIjYsAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBDQ9+KgAIHd5IbMAAAAAElFTkSuQmCC";
const { DateTime } = luxon;

patch(MailGuest, {
    new() {
        const record = super.new(...arguments);
        record.debouncedSetImStatus = debounce(
            (newStatus) => record.updateImStatus(newStatus),
            Store.IM_STATUS_DEBOUNCE_DELAY
        );
        return record;
    },
});

/** @this {import("models").MailGuest} */
function setup() {
    this.debouncedSetImStatus;
    this.monitorPresence = fields.Attr(false, {
        compute() {
            return this.store.env.services.bus_service.isActive && this.id > 0;
        },
    });
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
    /** @type {string|undefined} */
    this.previousPresencechannel;
    this.presenceChannel = fields.Attr(null, {
        compute() {
            const channel = `odoo-presence-mail.guest_${this.id}`;
            if (this.im_status_access_token) {
                return `${channel}-${this.im_status_access_token}`;
            }
            return channel;
        },
    });
}

patch(MailGuest.prototype, {
    setup() {
        super.setup(...arguments);
        setup.call(this);
    },
    get avatarUrl() {
        const accessTokenParam = {};
        if (this.store.self_user?.share !== false) {
            accessTokenParam.access_token = this.avatar_128_access_token;
        }
        if (this.id === -1) {
            return TRANSPARENT_AVATAR;
        }
        return imageUrl("mail.guest", this.id, "avatar_128", {
            ...accessTokenParam,
            unique: this.write_date,
        });
    },
    async updateGuestName(name) {
        await rpc("/mail/guest/update_name", {
            guest_id: this.id,
            name,
        });
    },
    updateImStatus(newStatus) {
        if (newStatus === "offline") {
            this.offline_since = DateTime.now();
        }
        this.im_status = newStatus;
    },
    _im_status_onUpdate() {
        if (this.eq(this.store.self_guest) && this.im_status === "offline" && this.id < 0) {
            this.store.env.services.im_status.updateBusPresence();
        }
    },
});

export { MailGuest };
