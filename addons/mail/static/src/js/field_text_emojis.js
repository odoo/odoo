/** @odoo-module **/

import MailEmojisMixin from '@mail/js/emojis_mixin';
import FieldEmojiCommon from '@mail/js/field_emojis_common';

import basicFields from 'web.basic_fields';
import registry from 'web.field_registry';

/**
 * Extension of the FieldText that will add emojis support
 */
var FieldTextEmojis = basicFields.FieldText.extend(MailEmojisMixin, FieldEmojiCommon);

registry.add('text_emojis', FieldTextEmojis);

export default FieldTextEmojis;
