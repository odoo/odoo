import { ResPartner } from "@mail/core/common/res_partner_model";
import { fields } from "@mail/model/export";

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

const { DateTime } = luxon;

/** @type {import("models").ResPartner} */
const resPartnerPatch = {
    setup() {
        super.setup(...arguments);
        this.meeting_until = fields.Datetime();
        this.onChange(
            () => [this.meeting_until],
            function onChangeMeetingUntil(meetingUntil) {
                if (!meetingUntil || meetingUntil <= DateTime.now()) {
                    return;
                }
                const timeout = window.setTimeout(() => {
                    this.meeting_until = false;
                }, Math.ceil(meetingUntil.diff(DateTime.now()).as("milliseconds")));
                return () => window.clearTimeout(timeout);
            },
            { immediate: true }
        );
    },
    /** @returns {string} */
    get inMeetingEndText() {
        if (this.isBot || !this.meeting_until || this.meeting_until <= DateTime.now()) {
            return "";
        }
        return _t("In a meeting until %(time)s", {
            time: this.meeting_until.toLocaleString(DateTime.TIME_SIMPLE),
        });
    },
};
patch(ResPartner.prototype, resPartnerPatch);
