/** @odoo-module **/

import emojis from '@mail/js/emojis';
const { Component } = owl;

class Emoji extends Component {
    /**
     * @override
     */
    setup () {
        // Mock the template variables:
        this.className = '';
        this.emojiListView = this.props.emojiListView;
    }
}

Emoji.template = 'mail.Emoji';
Emoji.props = {
    emoji: Object,
    emojiListView: Object,
};

class EmojiPicker extends Component {
    /**
     * @override
     */
    setup () {
        // Mock the template variables:
        this.emojis = emojis;
        this.className = '';
        this.emojiListView = {
            /**
             * @param {Event} event
             */
            onClickEmoji: event => {
                this.props.onClickEmoji(event.target.dataset.unicode);
            }
        };
    }

    /**
     * @param {Event} event
     */
    onRemoveEmoji (event) {
        this.props.onClickEmoji(false);
    }
}

EmojiPicker.template = 'knowledge.EmojiList';
EmojiPicker.props = ['onClickEmoji'];
EmojiPicker.components = { Emoji };

export default EmojiPicker;
