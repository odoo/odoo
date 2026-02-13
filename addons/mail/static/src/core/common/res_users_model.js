import { fields, Record } from "@mail/model/export";
import { debounce } from "@web/core/utils/timing";
import { Store } from "@mail/core/common/store_service";

const { DateTime } = luxon;

export class ResUsers extends Record {
    static _name = "res.users";
    static _inherits = { "res.partner": "partner_id" };

    static new() {
        const record = super.new(...arguments);
        record.debouncedSetImStatus = debounce(
            (newStatus) => (record.im_status = newStatus),
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

    /** @type {number} */
    id;
    company_id = fields.One("res.company");
    debouncedSetImStatus;
    /** @type {ImStatus} */
    im_status = fields.Attr(null, {
        onUpdate() {
            if (this.im_status === "offline") {
                if (this.eq(this.store.self_user)) {
                    this.store.env.services.im_status.updateBusPresence();
                }
                this.offline_since = DateTime.now();
            }
        },
    });
    /** @type {string|undefined} */
    im_status_access_token;
    /** @type {boolean} */
    is_admin;
    monitorPresence = fields.Attr(false, {
        compute() {
            return this.store.env.services.bus_service.isActive && this.id > 0;
        },
    });
    /** @type {"email" | "inbox"} */
    notification_type;
    /** @type {luxon.DateTime} */
    offline_since = fields.Datetime();
    partner_id = fields.One("res.partner", { inverse: "user_ids" });
    presenceChannel = fields.Attr(null, {
        compute() {
            const channel = `odoo-presence-res.users_${this.id}`;
            if (this.im_status_access_token) {
                return channel + `-${this.im_status_access_token}`;
            }
            return channel;
        },
    });
    /** @type {string|undefined} */
    previousPresencechannel;
    /** @type {boolean} false when the user is an internal user, true otherwise */
    share;
    /** @type {ReturnType<import("@odoo/owl").markup>|string|undefined} */
    signature = fields.Html(undefined);
}

ResUsers.register();
