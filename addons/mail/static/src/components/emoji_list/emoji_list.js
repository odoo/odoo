/** @odoo-module **/

import { useUpdate } from '@mail/component_hooks/use_update';
import emojis from '@mail/js/emojis';
import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { LegacyComponent } from '@web/legacy/legacy_component';

export class EmojiList extends LegacyComponent {

    /**
     * @override
     */
    setup() {
        super.setup();
        this.emojis = emojis;
        useUpdate({ func: () => this._update() });
    }

    get emojiListView() {
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

Object.assign(EmojiList, {
    props: { record: Object },
    template: 'mail.EmojiList',
});

registerMessagingComponent(EmojiList);
