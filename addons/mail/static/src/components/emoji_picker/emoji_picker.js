/** @odoo-module */

import emojiSections from '@mail/js/emojis_sections'
const { Component, useRef, useState, onMounted, onPatched } = owl;

class EmojiPicker extends Component {
    /**
     * @override
     */
    setup () {
        super.setup();
        this.root = useRef('root');
        this.input = useRef('search-input');
        this.uid = this.getUniqueID();
        this.sections = this.getEmojiSections();
        this.state = useState({
            term: '',
            sections: this.sections
        });
        onMounted(() => this._mounted());
        onPatched(() => this._patched());
    }

    /**
     * @returns {String}
     */
    getUniqueID () {
        return _.uniqueId('o_emoji_picker_');
    }

    /**
     * @returns {Object}
     */
    getEmojiSections () {
        return emojiSections;
    }

    /**
     * Callback function called when the user clicks on an emoji.
     * @param {Event} event
     */
    onEmojiClick (event) {
        if (this.props.onEmojiClick) {
            this.props.onEmojiClick(event);
        }
    }

    /**
     * Callback function called when the user clicks on a nav item.
     * @param {Event} event
     */
    onNavItemClick (event) {
        event.preventDefault();
        event.stopPropagation();
        const id = $(event.target).attr('href').substring(1);
        const $pane = $(this.root.el).find('.o_emoji_pane');
        const $section = $(this.root.el).find(`[id="${id}"]`);
        $pane.scrollTo($section, {
            duration: 100
        });
    }

    /**
     * Callback function called when the user types something on the search box.
     * @param {Event} event
     */
    _onInputChange (event) {
        const term = event.target.value;
        this.state.term = term;
        if (term.length === 0) {
            this.state.sections = this.sections;
            return;
        }
        const sections = [];
        for (const section of this.sections) {
            const emojis = section.emojis.filter(emoji => {
                return emoji[1].some(text => {
                    return text.indexOf(term) >= 0;
                });
            });
            if (emojis.length > 0) {
                sections.push({...section,
                    emojis: emojis
                });
            }
        }
        this.state.sections = sections;
    }

    /**
     * Callback function called when the user clicks on the reset button.
     * @param {Event} event
     */
    _onResetInput (event) {
        this.state.term = '';
        this.state.sections = this.sections;
    }

    /**
     * Callback function called when the component is mounted to the dom.
     */
    _mounted () {
        this.input.el.focus();
        const $pane = $(this.root.el).find('.o_emoji_pane');
        $pane.scrollspy();
    }

    /**
     * Callback function called when the component is patched
     */
    _patched () {
        const $pane = $(this.root.el).find('.o_emoji_pane');
        $pane.scrollspy('_process'); // refresh the navbar
    }
}

EmojiPicker.template = 'mail.EmojiPicker';
EmojiPicker.props = ['onEmojiClick'];

export default EmojiPicker;
