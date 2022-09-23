/** @odoo-module **/

import MailEmojisMixin from '@mail/js/emojis_mixin';
import EmojisFieldCommon from '@mail/views/fields/emojis_field_common';

import basicFields from 'web.basic_fields';
import registry from 'web.field_registry';

/**
 * Extension of the FieldText that will add emojis support
 */
var EmojisTextField = basicFields.FieldText.extend(MailEmojisMixin, EmojisFieldCommon);

registry.add('text_emojis', EmojisTextField);

export default EmojisTextField;
