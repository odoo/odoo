import { fields, Record } from "@mail/core/common/record";
import { imageUrl } from "@web/core/utils/urls";
import { rpc } from "@web/core/network/rpc";
import { debounce } from "@web/core/utils/timing";

const TRANSPARENT_AVATAR =
    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAIAAAACACAQAAABpN6lAAAAAqElEQVR42u3QMQEAAAwCoNm/9GJ4CBHIjYsAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBDQ9+KgAIHd5IbMAAAAAElFTkSuQmCC";
const { DateTime } = luxon;

export class MailGuest extends Record {
    static id = "id";
    static _name = "mail.guest";

    static new() {
        const record = super.new(...arguments);
        record.debouncedSetImStatus = debounce(
            (newStatus) => record.updateImStatus(newStatus),
            this.IM_STATUS_DEBOUNCE_DELAY
        );
        return record;
    }
    static IM_STATUS_DEBOUNCE_DELAY = 1000;

    /** @type {string} */
    avatar_128_access_token;
    /** @type {string} */
    commercial_company_name;
    /**
     * function = job position (Frenchism)
     *
     * @type {string}
     */
    function;
    /** @type {number} */
    id;
    /** @type {boolean | undefined} */
    is_company;
    /** @type {string} */
    phone;
    debouncedSetImStatus;
    displayName = fields.Attr(undefined, {
        compute() {
            return this._computeDisplayName();
        },
    });
    /** @type {ReturnType<import("@odoo/owl").markup>|string|undefined} */
    signature = fields.Html(undefined);
    monitorPresence = fields.Attr(false, {
        compute() {
            if (!this.store.env.services.bus_service.isActive || this.id <= 0) {
                return false;
            }
            return true;
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
    /** @type {'partner' | 'guest'} */
    type;
    /** @type {string} */
    name;
    country_id = fields.One("res.country");
    /** @type {string} */
    email;
    /** @type {ImStatus} */
    im_status = fields.Attr(null, {
        onUpdate() {
            if (this.eq(this.store.self) && this.im_status === "offline") {
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
            const parts = [
                "odoo-presence",
                `mail.guest_${this.id}`,
            ];
            if (this.im_status_access_token) {
                parts.push(this.im_status_access_token);
            }
            return parts.join("-");
        },
    });
    /** @type {boolean} */
    is_public;
    /** @type {'email' | 'inbox'} */
    notification_preference;
    isAdmin = false;
    isInternalUser = false;
    write_date = fields.Datetime();

    _computeDisplayName() {
        return this.name;
    }

    get avatarUrl() {
        const accessTokenParam = {};
        if (!this.store.self.isInternalUser) {
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

    searchChat() {
        return Object.values(this.store.Thread.records).find(
            (thread) => thread.channel_type === "chat" && thread.correspondent?.persona.eq(this)
        );
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

    _getActualModelName() {
        return MailGuest._name;
    }
}

MailGuest.register();
