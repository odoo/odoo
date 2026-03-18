import { ImStatusMixin } from "@mail/core/common/im_status_mixin";
import { fields } from "@mail/model/export";

import { rpc } from "@web/core/network/rpc";
import { imageUrl } from "@web/core/utils/urls";

const TRANSPARENT_AVATAR =
    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAIAAAACACAQAAABpN6lAAAAAqElEQVR42u3QMQEAAAwCoNm/9GJ4CBHIjYsAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBDQ9+KgAIHd5IbMAAAAAElFTkSuQmCC";

export class MailGuest extends ImStatusMixin {
    static _name = "mail.guest";

    /** @type {string} */
    avatar_128_access_token;
    /** @type {number} */
    id;
    /** @type {string} */
    name;
    country_id = fields.One("res.country");
    /** @type {string} */
    email;
    write_date = fields.Datetime();

    get avatarUrl() {
        const accessTokenParam = {};
        if (this.store.self_user?.share !== false) {
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
}

MailGuest.register();
