import { getKwArgs, models } from "@web/../tests/web_test_helpers";

export class MailGuest extends models.ServerModel {
    _name = "mail.guest";

    _get_guest_from_context() {
        const guestId = this.env.cookie.get("dgid");
        return guestId ? this.search_read([["id", "=", guestId]])[0] : null;
    }

    /**
     * @param {Number[]} ids
     * @returns {Record<string, ModelRecord>}
     */
    _to_store(store, fields) {
        const kwargs = getKwArgs(arguments, "store", "fields");
        fields = kwargs.fields;
        store._add_record_fields(
            this,
            fields.filter((field) => !["avatar_128"].includes(field))
        );
        for (const guest of this) {
            const data = {};
            if (fields.includes("avatar_128")) {
                data.avatar_128_access_token = guest.id;
                data.write_date = guest.write_date;
            }
            if (fields.includes("im_status")) {
                data.im_status = "offline";
                data.im_status_access_token = guest.id;
            }
            if (Object.keys(data).length) {
                store._add_record_fields(this.browse(guest.id), data);
            }
        }
    }

    get _to_store_defaults() {
        return ["avatar_128", "im_status", "name"];
    }

    _set_auth_cookie(guestId) {
        this.env.cookie.set("dgid", guestId);
    }
}
