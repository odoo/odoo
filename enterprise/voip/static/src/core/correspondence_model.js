import { url } from "@web/core/utils/urls";

export class Correspondence {
    activity;
    call;
    _partner;

    constructor({ activity, partner, call }) {
        if (!activity && !partner && !call) {
            throw TypeError(
                "Cannot create correspondence: missing required data. A correspondence must refer to an activity, a partner or a phone call."
            );
        }
        this.activity = activity;
        this._partner = partner;
        this.call = call;
    }

    /** @returns {string} */
    get avatarUrl() {
        if (this.partner) {
            return url("/web/image", {
                model: "res.partner",
                id: this.partner.id,
                field: "avatar_128",
            });
        }
        return "/base/static/img/avatar_grey.png";
    }

    /** @returns {import("@mail/core/common/persona_model").Persona | undefined} */
    get partner() {
        return this.call?.partner ?? this.activity?.partner ?? this._partner;
    }

    /** @returns {string} */
    get phoneNumber() {
        if (this.call) {
            return this.call.phoneNumber;
        }
        if (this.activity) {
            return this.activity.mobile || this.activity.phone;
        }
        if (this.partner) {
            return this.partner.mobileNumber || this.partner.landlineNumber;
        }
        return "";
    }
}
