import { ResPartner } from "@mail/core/common/res_partner_model";
import { fields } from "@mail/model/export";

import { browser } from "@web/core/browser/browser";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

const { DateTime } = luxon;

/** @type {import("models").ResPartner} */
const resPartnerPatch = {
    setup() {
        super.setup(...arguments);
        this.meeting_until = fields.Datetime(undefined, {
            onUpdate() {
                browser.clearTimeout(this._meetingUntilTimeout);
                this._meetingUntilTimeout = undefined;
                if (!this.meeting_until || this.meeting_until <= DateTime.now()) {
                    return;
                }
                this._meetingUntilTimeout = browser.setTimeout(() => {
                    this.meeting_until = false;
                }, this.meeting_until.diff(DateTime.now()).as("milliseconds"));
            },
        });
    },
    /** @returns {string} */
    get meetingStatus() {
        if (this.isBot || !this.meeting_until || this.meeting_until <= DateTime.now()) {
            return "";
        }
        return _t("In a meeting until %(time)s", {
            time: this.meeting_until.toLocaleString(DateTime.TIME_SIMPLE),
        });
    },
};
patch(ResPartner.prototype, resPartnerPatch);
