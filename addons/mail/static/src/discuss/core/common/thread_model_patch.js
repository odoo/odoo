/* @odoo-module */

import { Thread } from "@mail/core/common/thread_model";
import { assignDefined } from "@mail/utils/common/misc";

import { patch } from "@web/core/utils/patch";
import { url } from "@web/core/utils/urls";
import { _t } from "@web/core/l10n/translation";

patch(Thread.prototype, {
    get SETTINGS() {
        return [
            {
                id: false,
                name: _t("All Messages"),
            },
            {
                id: "mentions",
                name: _t("Mentions Only"),
            },
            {
                id: "no_notif",
                name: _t("Nothing"),
            },
        ];
    },
    get MUTES() {
        return [
            {
                id: "15_mins",
                value: 15,
                name: _t("For 15 minutes"),
            },
            {
                id: "1_hour",
                value: 60,
                name: _t("For 1 hour"),
            },
            {
                id: "3_hours",
                value: 180,
                name: _t("For 3 hours"),
            },
            {
                id: "8_hours",
                value: 480,
                name: _t("For 8 hours"),
            },
            {
                id: "24_hours",
                value: 1440,
                name: _t("For 24 hours"),
            },
            {
                id: "forever",
                value: -1,
                name: _t("Until I turn it back on"),
            },
        ];
    },
    get imgUrl() {
        if (this.type === "channel" || this.type === "group") {
            return url(
                `/discuss/channel/${this.id}/avatar_128`,
                assignDefined({}, { unique: this.avatarCacheKey })
            );
        }
        if (this.type === "chat") {
            return `/web/image/res.partner/${this.chatPartner.id}/avatar_128`;
        }
        return super.imgUrl;
    },
    update(data) {
        super.update(data);
        assignDefined(this, data, ["allow_public_upload"]);
    },
});
