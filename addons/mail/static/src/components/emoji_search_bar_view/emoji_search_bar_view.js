/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { useRefToModel } from '@mail/component_hooks/use_ref_to_model';
import { useUpdateToModel } from '@mail/component_hooks/use_update_to_model';


const { Component } = owl;

export class EmojiSearchBarView extends Component {
    /**
     * @override
     */
    setup() {
        super.setup();
        useRefToModel({ fieldName: 'inputRef', refName: 'input' });
        useUpdateToModel({ methodName: 'onComponentUpdate', modelName: 'EmojiSearchBarView' });
    }

    /**
     * @returns {EmojiSearchBarView}
     */
    get emojiSearchBarView() {
        return this.props.record;
    }
}

Object.assign(EmojiSearchBarView, {
    props: { record: Object },
    template: 'mail.EmojiSearchBarView',
});

registerMessagingComponent(EmojiSearchBarView);
