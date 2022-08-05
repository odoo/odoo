/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { useComponentToModel } from '@mail/component_hooks/use_component_to_model';

const { Component } = owl;

export class EmojiPickerView extends Component {
    setup() {
        useComponentToModel({ fieldName: 'component' });
    }
    /**
     * @returns {EmojiPickerView}
     */
    get emojiPickerView() {
        return this.props.record;
    }
}

Object.assign(EmojiPickerView, {
    props: { record: Object },
    template: 'mail.EmojiPickerView',
});

registerMessagingComponent(EmojiPickerView);
