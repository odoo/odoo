/** @odoo-module **/

import MailEmojisMixin from '@mail/js/emojis_mixin';
import EmojisFieldCommon from '@mail/views/fields/emojis_field_common';

import basicFields from 'web.basic_fields';
import registry from 'web.field_registry';

/**
 * Extension of the FieldChar that will add emojis support
 */
var EmojisCharField = basicFields.FieldChar.extend(MailEmojisMixin, EmojisFieldCommon);

registry.add('char_emojis', EmojisCharField);

export default EmojisCharField;
