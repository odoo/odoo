import { models } from "@web/../tests/web_test_helpers";

export class MailGuest extends models.ServerModel {
    _name = "mail.guest";

    _get_guest_from_context() {
        const guestId = this.env.cookie.get("dgid");
        return guestId ? this.search_read([["id", "=", guestId]])[0] : null;
    }

    _store_avatar_fields(res) {
        res.attr("avatar_128_access_token", (g) => g.id); // mock: token is the record id
        res.extend(["name", "write_date"]);
    }

    _store_im_status_fields(res) {
        res.attr("im_status", (g) => g.im_status || "offline");
        res.attr("im_status_access_token", (g) => g.id); // mock: token is the record id
    }

    _set_auth_cookie(guestId) {
        this.env.cookie.set("dgid", guestId);
    }
}
