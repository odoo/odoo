/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { useRefToModel } from '@mail/component_hooks/use_ref_to_model';
import { useUpdateToModel } from '@mail/component_hooks/use_update_to_model';

const { Component, onMounted } = owl;

export class EmojiGridView extends Component {
    setup() {
        useRefToModel({ fieldName: 'containerRef', refName: 'containerRef'});
        useRefToModel({ fieldName: 'listRef', refName: 'listRef'});
        useRefToModel({ fieldName: 'viewBlockRef', refName: 'viewBlockRef'});
        useUpdateToModel({ methodName: 'onComponentUpdate' });
        onMounted(() => {
            this.emojiGridView.calculateDimensions();
        });
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
