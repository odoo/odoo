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
    _to_store(ids, store, fields) {
        const kwargs = getKwArgs(arguments, "ids", "store", "fields");
        fields = kwargs.fields;
        if (!fields) {
            fields = ["avatar_128", "im_status", "name"];
        }
        for (const guest of this.browse(ids)) {
            const [data] = this._read_format(
                guest.id,
                fields.filter((field) => !["avatar_128"].includes(field)),
                false
            );
            if (fields.includes("avatar_128")) {
                data.avatar_128_access_token = guest.id;
                data.write_date = guest.write_date;
            }
            store.add(this.browse(guest.id), data);
        }
    }

    _set_auth_cookie(guestId) {
        this.env.cookie.set("dgid", guestId);
    }
}
