/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { useUpdate } from '@mail/component_hooks/use_update/use_update';
import { LegacyComponent } from '@web/legacy/legacy_component';
import EmojiPicker from '@mail/components/emoji_picker/emoji_picker';

export class EmojiList extends LegacyComponent {

    /**
     * @override
     */
    setup() {
        super.setup();
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

    /**
     * @param {Event} event
     */
    onEmojiClick(event) {
        if (this.emojiListView) {
            this.emojiListView.onClickEmoji(event);
        }
    }
}

Object.assign(EmojiList, {
    props: { localId: String },
    template: 'mail.EmojiList',
    components: { EmojiPicker },
});

registerMessagingComponent(EmojiList);
