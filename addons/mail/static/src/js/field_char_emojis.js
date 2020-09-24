odoo.define('mail.field_char_emojis', function (require) {
"use strict";

var basicFields = require('web.basic_fields');
var registry = require('web.field_registry');
var FieldEmojiCommon = require('mail.field_emojis_common');
var MailEmojisMixin = require('mail.emoji_mixin');

/**
 * Extension of the FieldChar that will add emojis support
 */
var FieldCharEmojis = basicFields.FieldChar.extend(MailEmojisMixin, FieldEmojiCommon);

registry.add('char_emojis', FieldCharEmojis);

return FieldCharEmojis;

});
