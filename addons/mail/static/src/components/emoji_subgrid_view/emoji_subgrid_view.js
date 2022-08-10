/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { useRefToModel } from '@mail/component_hooks/use_ref_to_model';

const { Component } = owl;

export class EmojiSubgridView extends Component {
    /**
     * @override
     */
    setup() {
        super.setup();
        useRefToModel({ fieldName: 'categoryNameRef', refName: 'name' });
    }
    /**
     * @returns {EmojiSubgridView}
     */
    get emojiSubgridView() {
        return this.props.record;
    }
}

Object.assign(EmojiSubgridView, {
    props: { record: Object },
    template: 'mail.EmojiSubgridView',
});

registerMessagingComponent(EmojiSubgridView);
