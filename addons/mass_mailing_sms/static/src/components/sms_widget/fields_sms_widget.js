/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";

import { SmsWidget } from "@sms/components/sms_widget/fields_sms_widget";

import { onWillStart } from "@odoo/owl";

const TEXT_URL_REGEX = /https?:\/\/[\w@:%.+&~#=/-]+(?:\?\S+)?/g;  // from tools.mail.TEXT_URL_REGEX

/**
 * Patch to provide extra characters count information to
 * consider links converted with link_tracker and opt-out
 * link if the option is selected.
 */
patch(SmsWidget.prototype, 'sms_widget_mass_mailing', {
    setup() {
        this._super(...arguments);
        this.orm = useService("orm");
        this.optOutEnabled = false;
        this.noticeLinksReplaced = false;
        this.linkReplacementsPlaceholders = null;

        onWillStart(async () => {
            if (this.props.record.resModel === "mailing.mailing") {
                const { unsubscribe, link } = await this.orm.call(
                    'mailing.mailing',
                    'get_sms_link_replacements_placeholders',
                    [this.res_id],
                );
                this.linkReplacementsPlaceholders = { unsubscribe, link };
                this.noticeLinksReplaced = false;
            }
        })
    },
    /**
     * @override
     */
    get nbrCharExplanation() {
        if (this.optOutEnabled) {
            return this.noticeLinksReplaced
                ? this.env._t(" (including link trackers and opt-out link) ")
                : this.env._t(" (including opt-out link) ");
        }
        return this.noticeLinksReplaced
            ? this.env._t(" (including link trackers) ")
            : this._super.apply(this, arguments); // Also default when no linkReplacementsPlaceholders
    },
    /**
     * @override
     */
    get nbrChar() {
        let res = this._super(...arguments);
        if (this.props.record.data.sms_allow_unsubscribe) {
            this.optOutEnabled = true;
            res += this.linkReplacementsPlaceholders.unsubscribe.length;
        }
        return res;
    },
    /**
     * @override
     */
    _getValueForSmsCounts(value) {
        let res = this._super(...arguments);
        if (this.linkReplacementsPlaceholders) {
            const replaced = res.replaceAll(TEXT_URL_REGEX, this.linkReplacementsPlaceholders.link);
            this.noticeLinksReplaced = replaced !== res;
            return replaced;
        }
        return res;
    },
});
