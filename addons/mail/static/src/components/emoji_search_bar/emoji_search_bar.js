/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { useRefToModel } from '@mail/component_hooks/use_ref_to_model';
import { useUpdateToModel } from '@mail/component_hooks/use_update_to_model';


const { Component } = owl;

export class EmojiSearchBar extends Component {
    /**
     * @override
     */
    setup() {
        super.setup();
        useRefToModel({ fieldName: 'inputRef', refName: 'input' });
        useUpdateToModel({ methodName: 'onComponentUpdate', modelName: 'EmojiSearchBar' });
    }
}

Object.assign(EmojiSearchBar, {
    props: {
        record: Object,
    },
    template: 'mail.EmojiSearchBar',
});

registerMessagingComponent(EmojiSearchBar);
