import { fields } from "@mail/model/export";
import { formatDateSimpleWithDay, formatDatetimeMedium } from "@mail/utils/common/dates";
import { Rating } from "@rating/core/common/rating_model";

import { _t } from "@web/core/l10n/translation";
import { user } from "@web/core/user";
import { patch } from "@web/core/utils/patch";

const { DateTime } = luxon;

patch(Rating.prototype, {
    setup() {
        super.setup(...arguments);
        /** @type {string|undefined} */
        this.publisher_avatar = undefined;
        /** @type {string|undefined} */
        this.publisher_comment = undefined;
        this.publisher_datetime = fields.Datetime();
        /** @type {number|false|undefined} */
        this.publisher_id = undefined;
        /** @type {string|undefined} */
        this.publisher_name = undefined;
        this.publisherDateText = this.computed(() => {
            const datetime = this.publisher_datetime;
            if (!datetime) {
                return false;
            }
            const startOfToday = this.store.startOfToday;
            const time = datetime.toLocaleString(DateTime.TIME_SIMPLE, { locale: user.lang });
            if (datetime.hasSame(startOfToday, "day")) {
                return _t("Published today at %(time)s", { time });
            }
            if (datetime.hasSame(startOfToday.minus({ day: 1 }), "day")) {
                return _t("Published yesterday at %(time)s", { time });
            }
            return _t("Published on %(date)s", {
                date: formatDateSimpleWithDay(datetime, startOfToday),
            });
        });
        this.publisherDatetimeMedium = this.computed(
            () => this.publisher_datetime && formatDatetimeMedium(this.publisher_datetime)
        );
    },
});
