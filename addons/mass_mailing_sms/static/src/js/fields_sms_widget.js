/** @odoo-module **/

import { _t } from "web.core";
import SmsWidget from '@sms/js/fields_sms_widget';

const TEXT_URL_REGEX = /https?:\/\/[\w@:%.+&~#=/-]+(?:\?\S+)?/g;  // from tools.mail.TEXT_URL_REGEX

/**
 * Override to provide extra characters count information to
 * consider links converted with link_tracker and opt-out
 * link if the option is selected.
 */
SmsWidget.include({
    events: _.extend({}, SmsWidget.prototype.events || {}, {
        'focusin': '_onClick',
    }),
    /**
     *@override
     */
    willStart: async function () {
        await this._super.apply(this, arguments);
        if (this.model === "mailing.mailing" && this.mode === 'edit') {
            const { unsubscribe, link } = await this._rpc({
                model: 'mailing.mailing',
                method: 'get_sms_link_replacements_placeholders',
                args: [this.res_id]
            });
            this.linkReplacementsPlaceholders = { unsubscribe, link };
            this.noticeLinksReplaced = false;
        }
    },
    /**
     * Add the characters for opt-out link if enabled.
     *
     * @override
     */
    _compute: function() {
        this._super.apply(this, arguments);
        if (!this.linkReplacementsPlaceholders) {
            return;
        }
        // this is the simplest way to read from another field in a legacy fix.
        const unsubscribe_el = document.querySelector('div[name="sms_allow_unsubscribe"] input');
        if (unsubscribe_el && unsubscribe_el.checked) {
            this.optOutEnabled = true;
            this.nbrChar += this.linkReplacementsPlaceholders.unsubscribe.length;
        }
    },
    /**
     * Add the applicable extra characters notice.
     *
     * @override
     */
    _getNbrCharExplanationTemplate: function () {
        if (this.optOutEnabled) {
            return this.noticeLinksReplaced
                ? _t("%s characters (including link trackers and opt-out link), fits in %s SMS (%s) ")
                : _t("%s characters (including opt-out link), fits in %s SMS (%s) ");
        }
        return this.noticeLinksReplaced
            ? _t("%s characters (including link trackers), fits in %s SMS (%s) ")
            : this._super.apply(this, arguments); // Also default when no linkReplacementsPlaceholders
    },
    /**
     * Convert links to link trackers-length replacements.
     * Works under the assumption that these trackers urls only
     * contain GSM7 characters.
     *
     * @override
     */
    _getValueForSmsCounts: function () {
        const value = this._super.apply(this, arguments);
        if (this.linkReplacementsPlaceholders) {
            const replaced = value.replaceAll(TEXT_URL_REGEX, this.linkReplacementsPlaceholders.link);
            this.noticeLinksReplaced = replaced !== value;
            return replaced;
        }
        return value;
    },
    _onClick: function() {
        this._super.apply(this, arguments);
        if (this.linkReplacementsPlaceholders) {  // covers mailing and edit mode
            this._updateSMSInfo();
        }
    }
});
