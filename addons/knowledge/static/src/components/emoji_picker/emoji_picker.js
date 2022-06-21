/** @odoo-module **/

import emojis from '@mail/js/emojis';
const { Component } = owl;

class LegacyEmoji extends Component {
    /**
     * @override
     */
    setup () {
        // Mock the template variables:
        this.className = '';
        this.emojiListView = this.props.emojiListView;
    }
}

LegacyEmoji.template = 'mail.LegacyEmoji';
LegacyEmoji.props = {
    emojiView: Object
};

class EmojiPicker extends Component {
    /**
     * @override
     */
    setup () {
        // Mock the template variables:
        this.className = '';
        const viewEventHandlers =  {
            /**
             * @param {Event} event
             */
            onClickEmoji: event => {
                this.props.onClickEmoji(event.target.dataset.unicode);
            },
        };
        this.emojiListView = {
            emojiViews: emojis.map((emoji, index) => {
                return {
                    localId: index,
                    emoji: emoji,
                    emojiListView: viewEventHandlers
                };
            })
        };
    }

    /**
     * @param {Event} event
     */
    onRemoveEmoji (event) {
        this.props.onClickEmoji(false);
    }
}

EmojiPicker.template = 'knowledge.LegacyEmojiList';
EmojiPicker.props = ['onClickEmoji'];
EmojiPicker.components = { LegacyEmoji };

export default EmojiPicker;
