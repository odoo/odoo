import { AND, Record } from "@mail/core/common/record";
import { imageUrl } from "@web/core/utils/urls";
import { rpcWithEnv } from "@mail/utils/common/misc";

/**
 * @typedef {'offline' | 'bot' | 'online' | 'away' | 'im_partner' | undefined} ImStatus
 * @typedef Data
 * @property {number} id
 * @property {string} name
 * @property {string} email
 * @property {'partner'|'guest'} type
 * @property {ImStatus} im_status
 */

let rpc;
export class Persona extends Record {
    static id = AND("type", "id");
    /** @type {Object.<number, import("models").Persona>} */
    static records = {};
    /** @returns {import("models").Persona} */
    static get(data) {
        return super.get(data);
    }
    /** @returns {import("models").Persona|import("models").Persona[]} */
    static insert(data) {
        return super.insert(...arguments);
    }
    static new() {
        rpc = rpcWithEnv(this.store.env);
        return super.new(...arguments);
    }

    channelMembers = Record.many("ChannelMember");
    /** @type {number} */
    id;
    /** @type {boolean | undefined} */
    is_company;
    /** @type {string} */
    landlineNumber;
    /** @type {string} */
    mobileNumber;
    storeAsTrackedImStatus = Record.one("Store", {
        /** @this {import("models").Persona} */
        compute() {
            if (this.type === "partner" && this.im_status !== "im_partner" && !this.is_public) {
                return this.store;
            }
        },
        eager: true,
        inverse: "imStatusTrackedPersonas",
    });
    /** @type {'partner' | 'guest'} */
    type;
    /** @type {string} */
    name;
    /** @type {string} */
    displayName;
    country = Record.one("Country");
    /** @type {string} */
    email;
    /** @type {number} */
    userId;
    /** @type {ImStatus} */
    im_status;
    /** @type {'email' | 'inbox'} */
    notification_preference;
    isAdmin = false;
    isInternalUser = false;
    /** @type {luxon.DateTime} */
    write_date = Record.attr(undefined, { type: "datetime" });

    /**
     * @returns {boolean}
     */
    get hasPhoneNumber() {
        return Boolean(this.mobileNumber || this.landlineNumber);
    }

    get nameOrDisplayName() {
        return this.name || this.displayName;
    }

    get emailWithoutDomain() {
        return this.email.substring(0, this.email.lastIndexOf("@"));
    }

    get avatarUrl() {
        if (this.type === "partner") {
            return imageUrl("res.partner", this.id, "avatar_128", { unique: this.write_date });
        }
        if (this.type === "guest") {
            return imageUrl("mail.guest", this.id, "avatar_128", { unique: this.write_date });
        }
        if (this.userId) {
            return imageUrl("res.users", this.userId, "avatar_128", { unique: this.write_date });
        }
        return this.store.DEFAULT_AVATAR;
    }

    searchChat() {
        return Object.values(this.store.Thread.records).find(
            (thread) => thread.channel_type === "chat" && thread.correspondent?.eq(this)
        );
    }

    async updateGuestName(name) {
        await rpc("/mail/guest/update_name", {
            guest_id: this.id,
            name,
        });
    }
}

Persona.register();
