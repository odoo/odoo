odoo.define('mail.field_text_emojis', function (require) {
"use strict";

var basicFields = require('web.basic_fields');
var registry = require('web.field_registry');
var FieldEmojiCommon = require('mail.field_emojis_common');
var MailEmojisMixin = require('mail.emoji_mixin');

/**
 * Extension of the FieldText that will add emojis support
 */
var FieldTextEmojis = basicFields.FieldText.extend(MailEmojisMixin, FieldEmojiCommon);

registry.add('text_emojis', FieldTextEmojis);

return FieldTextEmojis;

});
