/** @odoo-module **/

import Widget from 'web.Widget';
import { ComponentWrapper, WidgetAdapterMixin } from 'web.OwlCompatibility';
import EmojiPicker from '../../components/emoji_picker/emoji_picker.js';

const EmojiPickerWidget = Widget.extend(WidgetAdapterMixin, {
    events: {
        'click .dropdown-menu': '_onDropdownClick'
    },

    /**
     * @override
     * @param {Object} parent
     * @param {Object} options
     * @param {integer} options.article_id
     */
    init: function (parent, options) {
        this._super.apply(this, arguments);
        this.options = options;
    },

    /**
     * @override
     */
    start: function () {
        this.component = new ComponentWrapper(this, EmojiPicker, {
            /**
             * @param {String} unicode
             */
            onClickEmoji: unicode => {
                this.trigger_up('emoji_click', {
                    articleId: this.options.article_id,
                    unicode: unicode || false,
                });
                this.close();
            },
        });
        const menu = this.el.querySelector('.dropdown-menu');
        return this.component.mount(menu);
    },

    /**
     * Closes the dropdown
     */
    close: function () {
        this.$('.dropdown-menu').removeClass('show');
    },

    /**
     * @param {Event} event
     */
    _onDropdownClick: function (event) {
        event.preventDefault();
        event.stopPropagation();
    },
});

export default EmojiPickerWidget;
