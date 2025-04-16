import { AND, fields, Record } from "@mail/core/common/record";
import { imageUrl } from "@web/core/utils/urls";
import { rpc } from "@web/core/network/rpc";
import { debounce } from "@web/core/utils/timing";

const TRANSPARENT_AVATAR =
    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAIAAAACACAQAAABpN6lAAAAAqElEQVR42u3QMQEAAAwCoNm/9GJ4CBHIjYsAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBDQ9+KgAIHd5IbMAAAAAElFTkSuQmCC";
const { DateTime } = luxon;

/**
 * @typedef {'offline' | 'bot' | 'online' | 'away' | 'im_partner' | undefined} ImStatus
 * @typedef Data
 * @property {number} id
 * @property {string} name
 * @property {string} email
 * @property {'partner'|'guest'} type
 * @property {ImStatus} im_status
 */

export class Persona extends Record {
    static id = AND("type", "id");
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
    /** @type {ReturnType<import("@odoo/owl").markup>|string|undefined} */
    signature = fields.Html(undefined);
    storeAsTrackedImStatus = fields.One("Store", {
        /** @this {import("models").Persona} */
        compute() {
            if (
                this.type === "guest" ||
                (this.type === "partner" && this.im_status !== "im_partner" && !this.is_public)
            ) {
                return this.store;
            }
        },
        onAdd() {
            if (!this.store.env.services.bus_service.isActive) {
                return;
            }
            const model = this.type === "partner" ? "res.partner" : "mail.guest";
            this.store.env.services.bus_service.addChannel(`odoo-presence-${model}_${this.id}`);
        },
        onDelete() {
            if (!this.store.env.services.bus_service.isActive) {
                return;
            }
            const model = this.type === "partner" ? "res.partner" : "mail.guest";
            this.store.env.services.bus_service.deleteChannel(`odoo-presence-${model}_${this.id}`);
        },
        eager: true,
        inverse: "imStatusTrackedPersonas",
    });
    /** @type {'partner' | 'guest'} */
    type;
    /** @type {string} */
    name;
    country = fields.One("res.country");
    /** @type {string} */
    email;
    /** @type {number} */
    userId;
    /** @type {ImStatus} */
    im_status = fields.Attr(null, {
        onUpdate() {
            if (this.eq(this.store.self) && this.im_status === "offline") {
                this.store.env.services.im_status.updateBusPresence();
            }
        },
    });
    last_poll = fields.Datetime();
    /** @type {boolean} */
    is_public;
    /** @type {'email' | 'inbox'} */
    notification_preference;
    isAdmin = false;
    isInternalUser = false;
    write_date = fields.Datetime();
    group_ids = fields.Many("res.groups", { inverse: "personas" });

    get emailWithoutDomain() {
        return this.email.substring(0, this.email.lastIndexOf("@"));
    }

    get avatarUrl() {
        const accessTokenParam = {};
        if (!this.store.self.isInternalUser) {
            accessTokenParam.access_token = this.avatar_128_access_token;
        }
        if (this.type === "partner") {
            return imageUrl("res.partner", this.id, "avatar_128", {
                ...accessTokenParam,
                unique: this.write_date,
            });
        }
        if (this.type === "guest") {
            if (this.id === -1) {
                return TRANSPARENT_AVATAR;
            }
            return imageUrl("mail.guest", this.id, "avatar_128", {
                ...accessTokenParam,
                unique: this.write_date,
            });
        }
        if (this.userId) {
            return imageUrl("res.users", this.userId, "avatar_128", {
                unique: this.write_date,
            });
        }
        return this.store.DEFAULT_AVATAR;
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
            this.last_poll = DateTime.now();
        }
        this.im_status = newStatus;
    }

    _getActualModelName() {
        return this.type === "partner"
            ? "res.partner"
            : this.type === "visitor"
            ? "website.visitor"
            : "mail.guest";
    }
}

Persona.register();
