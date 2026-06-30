import { fields, Record } from "@mail/core/common/record";
import { imageUrl } from "@web/core/utils/urls";
import { rpc } from "@web/core/network/rpc";
import { debounce } from "@web/core/utils/timing";
import { Store } from "@mail/core/common/store_service";

const TRANSPARENT_AVATAR =
    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAIAAAACACAQAAABpN6lAAAAAqElEQVR42u3QMQEAAAwCoNm/9GJ4CBHIjYsAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBDQ9+KgAIHd5IbMAAAAAElFTkSuQmCC";
const { DateTime } = luxon;

/**
 * @typedef {'offline' | 'bot' | 'online' | 'away' | 'im_partner' | undefined} ImStatus
 * @typedef Data
 * @property {number} id
 * @property {string} name
 * @property {string} email
 * @property {ImStatus} im_status
 */

export class MailGuest extends Record {
    static id = "id";
    static _name = "mail.guest";
    static new() {
        const record = super.new(...arguments);
        record.debouncedSetImStatus = debounce(
            (newStatus) => record.updateImStatus(newStatus),
            Store.IM_STATUS_DEBOUNCE_DELAY
        );
        return record;
    }

    /** @type {string} */
    avatar_128_access_token;
    /** @type {number} */
    id;
    debouncedSetImStatus;
    monitorPresence = fields.Attr(false, {
        compute() {
            return this.store.env.services.bus_service.isActive && this.id > 0;
        },
    });
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
    name;
    country_id = fields.One("res.country");
    /** @type {string} */
    email;
    /** @type {ImStatus} */
    im_status = fields.Attr(null, {
        onUpdate() {
            if (this.eq(this.store.self_guest) && this.im_status === "offline" && this.id < 0) {
                this.store.env.services.im_status.updateBusPresence();
            }
        },
    });
    /** @type {string|undefined} */
    im_status_access_token;

    /** @type {luxon.DateTime} */
    offline_since = fields.Datetime();
    /** @type {string|undefined} */
    previousPresencechannel;
    presenceChannel = fields.Attr(null, {
        compute() {
            const channel = `odoo-presence-mail.guest_${this.id}`;
            if (this.im_status_access_token) {
                return `${channel}-${this.im_status_access_token}`;
            }
            return channel;
        },
    });
    write_date = fields.Datetime();

    get avatarUrl() {
        const accessTokenParam = {};
        if (this.store.self.main_user_id?.share !== false) {
            accessTokenParam.access_token = this.avatar_128_access_token;
        }
        if (this.id === -1) {
            return TRANSPARENT_AVATAR;
        }
        return imageUrl("mail.guest", this.id, "avatar_128", {
            ...accessTokenParam,
            unique: this.write_date,
        });
    }

    async updateGuestName(name) {
        await rpc("/mail/guest/update_name", {
            guest_id: this.id,
            name,
        });
    }

    updateImStatus(newStatus) {
        if (newStatus === "offline") {
            this.offline_since = DateTime.now();
        }
        this.im_status = newStatus;
    }
}

MailGuest.register();
