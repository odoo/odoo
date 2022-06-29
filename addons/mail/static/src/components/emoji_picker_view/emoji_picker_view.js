/** @odoo-module **/

import { useUpdate } from '@mail/component_hooks/use_update';
import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { LegacyComponent } from '@web/legacy/legacy_component';

export class EmojiPickerView extends LegacyComponent {

    /**
     * @override
     */
    setup() {
        super.setup();        
        useUpdate({ func: () => this._update() });
    }

    get emojiPickerView() {
        return this.props.record;
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _update() {
        this.trigger('o-popover-compute');
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    close() {
        this.trigger('o-popover-close');
    }

    /**
     * Returns whether the given node is self or a children of self.
     *
     * @param {Node} node
     * @returns {boolean}
     */
    contains(node) {
        return Boolean(this.root.el && this.root.el.contains(node));
    }

}

Object.assign(EmojiPickerView, {
    props: { record: Object },
    template: 'mail.EmojiPickerView',
});

registerMessagingComponent(EmojiPickerView);
