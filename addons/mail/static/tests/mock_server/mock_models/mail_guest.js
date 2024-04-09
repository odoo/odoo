import { models } from "@web/../tests/web_test_helpers";

export class MailGuest extends models.ServerModel {
    _name = "mail.guest";

    _get_guest_from_context() {
        const guestId = this.env.cookie.get("dgid");
        return guestId ? this.search_read([["id", "=", guestId]])[0] : null;
    }

    _init_messaging() {
        return {
            Store: {
<<<<<<< HEAD
                initBusId: this.lastBusNotificationId,
||||||| parent of 9a5600b4f823 (temp)
                initBusId: this.lastBusNotificationId, // deprecated, last id should be checked per field
=======
                initBusId: this.env["bus.bus"].lastBusNotificationId, // deprecated, last id should be checked per field
>>>>>>> 9a5600b4f823 (temp)
            },
        };
    }

    /**
     * @param {Number[]} ids
     * @returns {Record<string, ModelRecord>}
     */
    _guest_format(ids) {
        const guests = this._filter([["id", "in", ids]], { active_test: false });
        return Object.fromEntries(
            guests.map((guest) => {
                return [
                    guest.id,
                    {
                        id: guest.id,
                        im_status: guest.im_status,
                        name: guest.name,
                        type: "guest",
                        write_date: guest.write_date,
                    },
                ];
            })
        );
    }

    _set_auth_cookie(guestId) {
        this.env.cookie.set("dgid", guestId);
    }
}
