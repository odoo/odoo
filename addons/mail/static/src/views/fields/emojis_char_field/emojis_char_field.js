/** @odoo-module **/

import { CharField } from "@web/views/fields/char/char_field";
import { patch } from "@web/core/utils/patch";
import MailEmojisMixin from '@mail/js/emojis_mixin';
import { EmojisDropdown } from '@mail/js/emojis_dropdown';
import { EmojisFieldCommon } from '@mail/views/fields/emojis_field_common';
import { registry } from "@web/core/registry";

const { useRef } = owl;

/**
 * Extension of the FieldChar that will add emojis support
 */
export class EmojisCharField extends CharField {
    setup() {
        super.setup();
        this.targetEditElement = useRef('input');
        this._setupOverride();
    }
};

patch(EmojisCharField.prototype, 'emojis_char_field_mail_mixin', MailEmojisMixin);
patch(EmojisCharField.prototype, 'emojis_char_field_field_mixin', EmojisFieldCommon);
EmojisCharField.template = 'mail.EmojisCharField';
EmojisCharField.components = { ...CharField.components, EmojisDropdown };
EmojisCharField.additionalClasses = [...(CharField.additionalClasses || []), 'o_field_text'];
registry.category("fields").add("char_emojis", EmojisCharField);
