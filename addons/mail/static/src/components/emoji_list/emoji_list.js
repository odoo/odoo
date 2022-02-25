/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { useUpdate } from '@mail/component_hooks/use_update/use_update';
import emojis from '@mail/js/emojis';
import { LegacyComponent } from '@web/legacy/legacy_component';

const { Component } = owl;

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
        return this.messaging && this.messaging.models['EmojiListView'].get(this.props.localId);
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
    props: { localId: String },
    template: 'mail.EmojiList',
});

registerMessagingComponent(EmojiList);
