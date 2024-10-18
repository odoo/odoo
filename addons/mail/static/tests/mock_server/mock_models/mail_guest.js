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
            fields = ["im_status", "name", "write_date"];
        }
        store.add("mail.guest", this._read_format(ids, fields, false));
    }

    _set_auth_cookie(guestId) {
        this.env.cookie.set("dgid", guestId);
    }
}
