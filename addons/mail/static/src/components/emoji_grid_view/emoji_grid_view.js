/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { useComponentToModel } from '@mail/component_hooks/use_component_to_model';
import { useRefToModel } from '@mail/component_hooks/use_ref_to_model';

const { Component } = owl;

export class EmojiGridView extends Component {
    /**
     * @override
     */
    setup() {
        super.setup();
        useComponentToModel({ fieldName: 'component' });
        useRefToModel({ fieldName: 'thresholdLineForStickyRef', refName: 'thresholdLineForSticky'});
    }
    /**
     * @returns {EmojiGridView}
     */
    get emojiGridView() {
        return this.props.record;
    }
}

Object.assign(EmojiGridView, {
    props: { record: Object },
    template: 'mail.EmojiGridView',
});

registerMessagingComponent(EmojiGridView);
