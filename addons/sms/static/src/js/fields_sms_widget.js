/** @odoo-module **/

import { _t } from 'web.core';
import fieldRegistry from 'web.field_registry';
import FieldTextEmojis from '@mail/js/field_text_emojis';
/**
 * SmsWidget is a widget to display a textarea (the body) and a text representing
 * the number of SMS and the number of characters. This text is computed every
 * time the user changes the body.
 */
var SmsWidget = FieldTextEmojis.extend({
    className: 'o_field_text',
    enableEmojis: false,
    /**
     * @constructor
     */
    init: function () {
        this._super.apply(this, arguments);
        this.nbrChar = 0;
        this.nbrSMS = 0;
        this.encoding = 'GSM7';
        this.enableEmojis = !!this.nodeOptions.enable_emojis;
    },

    /**
     * @override
     *"This will add the emoji dropdown to a target field (controlled by the "enableEmojis" attribute)
     */
    on_attach_callback: function () {
        if (this.enableEmojis) {
            this._super.apply(this, arguments);
        }
    },

    //--------------------------------------------------------------------------
    // Private: override widget
    //--------------------------------------------------------------------------

    /**
     * @private
     * @override
     */
    _renderEdit: function () {
        var def = this._super.apply(this, arguments);

        this._compute();
        $('.o_sms_container').remove();
        var $sms_container = $('<div class="o_sms_container"/>');
        $sms_container.append(this._renderSMSInfo());
        $sms_container.append(this._renderIAPButton());
        this.$el = this.$el.add($sms_container);

        return def;
    },

    //--------------------------------------------------------------------------
    // Private: SMS
    //--------------------------------------------------------------------------

    /**
     * Compute the number of characters and sms
     * @private
     */
    _compute: function () {
        var content = this._getValue();
        this.encoding = this._extractEncoding(content);
        this.nbrChar = content.length;
        this.nbrChar += (content.match(/\n/g) || []).length;
        this.nbrSMS = this._countSMS(this.nbrChar, this.encoding);
    },

    /**
     * Count the number of SMS of the content
     * @private
     * @returns {integer} Number of SMS
     */
    _countSMS: function () {
        if (this.nbrChar === 0) {
            return 0;
        }
        if (this.encoding === 'UNICODE') {
            if (this.nbrChar <= 70) {
                return 1;
            }
            return Math.ceil(this.nbrChar / 67);
        }
        if (this.nbrChar <= 160) {
            return 1;
        }
        return Math.ceil(this.nbrChar / 153);
    },

    /**
     * Extract the encoding depending on the characters in the content
     * @private
     * @param {String} content Content of the SMS
     * @returns {String} Encoding of the content (GSM7 or UNICODE)
     */
    _extractEncoding: function (content) {
        if (String(content).match(RegExp("^[@£$¥èéùìòÇ\\nØø\\rÅåΔ_ΦΓΛΩΠΨΣΘΞÆæßÉ !\\\"#¤%&'()*+,-./0123456789:;<=>?¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§¿abcdefghijklmnopqrstuvwxyzäöñüà]*$"))) {
            return 'GSM7';
        }
        return 'UNICODE';
    },

    /**
     * Render the IAP button to redirect to IAP pricing
     * @private
     */
    _renderIAPButton: function () {
        return $('<a>', {
            'href': 'https://iap-services.odoo.com/iap/sms/pricing',
            'target': '_blank',
            'title': _t('SMS Pricing'),
            'aria-label': _t('SMS Pricing'),
            'class': 'fa fa-lg fa-info-circle',
        });
    },

    /**
     * Render the number of characters, sms and the encoding.
     * @private
     */
    _renderSMSInfo: function () {
        var string = _.str.sprintf(_t('%s characters, fits in %s SMS (%s) '), this.nbrChar, this.nbrSMS, this.encoding);
        var $span = $('<span>', {
            'class': 'text-muted o_sms_count',
        });
        $span.text(string);
        return $span;
    },

    /**
     * Update widget SMS information with re-computed info about length, ...
     * @private
     */
    _updateSMSInfo: function ()  {
        this._compute();
        var string = _.str.sprintf(_t('%s characters, fits in %s SMS (%s) '), this.nbrChar, this.nbrSMS, this.encoding);
        this.$('.o_sms_count').text(string);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @override
     * @private
     */
    _onBlur: function () {
        var content = this._getValue();
        if( !content.trim().length && content.length > 0) {
            this.displayNotification({ title: _t("Your SMS Text Message must include at least one non-whitespace character"), type: 'danger' });
            this.$input.val(content.trim());
            this._updateSMSInfo();
        }
    },

    /**
     * @override
     * @private
     */
    _onChange: function () {
        this._super.apply(this, arguments);
        this._updateSMSInfo();
    },

    /**
     * @override
     * @private
     */
    _onInput: function () {
        this._super.apply(this, arguments);
        this._updateSMSInfo();
    },
});

fieldRegistry.add('sms_widget', SmsWidget);

export default SmsWidget;
