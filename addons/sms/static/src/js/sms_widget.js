odoo.define('sms.sms_widget', function (require) {
"use strict";

var basicFields = require('web.basic_fields');
var core = require('web.core');
var fieldRegistry = require('web.field_registry');
var dom = require('web.dom');
var framework = require('web.framework');


var FieldText = basicFields.FieldText;
var InputField = basicFields.InputField;
var QWeb = core.qweb;

var _t = core._t
/**
 * SmsWidget is a widget to display a textarea (the body) and a text representing
 * the number of SMS and the number of characters. This text is computed every
 * time the user changes the body.
 */
var SmsWidget = InputField.extend({
    /**
     * @constructor
     */
    init: function () {
        this._super.apply(this, arguments);
        this.nbrChar = 0;
        this.nbrSMS = 0;
        this.encoding = "GSM7";
        this.tagName = 'div';
    },

    //--------------------------------------------------------------------------
    // Private
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
        this._renderSMS();
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
     * @private
     * @override
     */
    _renderEdit: function () {
        this.$el.empty();
        this._prepareInput($('<textarea/>')).appendTo(this.$el);
        this.$el.append($(QWeb.render("sms.sms_count", {})));
        this._compute();
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
     * Render the number of characters, sms and the encoding.
     * @private
     */
    _renderSMS: function () {
        this.$('.o_sms_count').text(_.str.sprintf(_t('%s chars, fits in %s SMS (%s) '), this.nbrChar, this.nbrSMS, this.encoding));
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------   

    /**
     * @override
     * @private
     */
    _onChange: function () {
        this._super.apply(this, arguments);
        this._compute();
    },
    /**
     * @override
     * @private
     */
    _onInput: function () {
        this._super.apply(this, arguments);
        this._compute();
    },
});

fieldRegistry.add('sms_widget', SmsWidget);

return SmsWidget;
});
