/** @odoo-module **/

import MailEmojisMixin from '@mail/js/emojis_mixin';
import FieldEmojiCommon from '@mail/js/field_emojis_common';

import basicFields from 'web.basic_fields';
import registry from 'web.field_registry';

/**
 * Extension of the FieldChar that will add emojis support
 */
var FieldCharEmojis = basicFields.FieldChar.extend(MailEmojisMixin, FieldEmojiCommon);

registry.add('char_emojis', FieldCharEmojis);

export default FieldCharEmojis;
