/** @odoo-module **/

import emojis from '@mail/js/emojis';
import MailEmojisMixin from '@mail/js/emojis_mixin';
import { qweb as QWeb } from 'web.core';
import Widget from 'web.Widget';
import { ComponentWrapper, WidgetAdapterMixin } from 'web.OwlCompatibility';
import EmojiPicker from '@mail/components/emoji_picker/emoji_picker';

var _onEmojiClickMixin = MailEmojisMixin._onEmojiClick;

/**
 * The mixin will be used in a definition field. As you may know, A field is a widget.
 * To instantiate the emoji picker, we will have the use the following adapter.
 */
const EmojiPickerLegacy = Widget.extend(WidgetAdapterMixin, {
    /**
     * @override
     * @param {Object} parent
     * @param {Object} options
     * @param {Function} options.onEmojiClick - Callback function
     */
    init: function (parent, options) {
        this._super.apply(this, arguments);
        this.options = options;
    },
    /**
     * @override
     */
    start: function () {
        this.component = new ComponentWrapper(this, EmojiPicker, this.options);
        return this.component.mount(this.el);
    },
});

/*
 * Common code for FieldTextEmojis and FieldCharEmojis
 */
var FieldEmojiCommon = {
    /**
     * @override
     * @private
     */
    init: function () {
        this._super.apply(this, arguments);
        this._triggerOnchange = _.debounce(this._triggerOnchange, 2000);
        this.emojis = emojis;
    },

    /**
     * @override
     */
    on_attach_callback: function () {
        this._attachEmojisDropdown();
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @override
     * @private
     */
    _render: function () {
        this._super.apply(this, arguments);

        if (this.mode !== 'edit') {
            this.$el.html(this._formatText(this.$el.text()));
        }
    },

    /**
     * Overridden because we need to add the Emoji to the input AND trigger
     * the 'change' event to refresh the value.
     *
     * @override
     * @private
     */
    _onEmojiClick: function () {
        _onEmojiClickMixin.apply(this, arguments);
        this._isDirty = true;
        this.$input.trigger('change');
    },

    /**
     *
     * By default, the 'change' event is only triggered when the text element is blurred.
     *
     * We override this method because we want to update the value while
     * the user is typing his message (and not only on blur).
     *
     * @override
     * @private
     */
    _onKeydown: function () {
        this._super.apply(this, arguments);
        if (this.nodeOptions.onchange_on_keydown) {
            this._triggerOnchange();
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Used by MailEmojisMixin, check its document for more info.
     *
     * @private
     */
    _getTargetTextElement() {
        return this.$el;
    },

    /**
     * Triggers the 'change' event to refresh the value.
     * This method is debounced to run 2 seconds after typing ends.
     * (to avoid spamming the server while the user is typing his message)
     *
     * @private
     */
    _triggerOnchange: function () {
        this.$input.trigger('change');
    },

    /**
     * This will add an emoji button that shows the emojis selection dropdown.
     *
     * Should be used inside 'on_attach_callback' because we need the element to be attached to the form first.
     * That's because the $emojisIcon element needs to be rendered outside of this $el
     * (which is an text element, that can't 'contain' any other elements).
     *
     * @private
     */
    _attachEmojisDropdown: function () {
        if (!this.$emojisIcon) {
            this.$emojisIcon = $(QWeb.render('mail.EmojisDropdown', {widget: this}));

            const $dropdown = this.$emojisIcon.find('.dropdown-menu');
            const $toggle = this.$emojisIcon.find('.dropdown-toggle');
            $toggle.one('click', () => {
                const picker = new EmojiPickerLegacy(this, {
                    onEmojiClick: this._onEmojiClick.bind(this)
                });
                picker.attachTo($dropdown);
            });

            if (this.$el.filter('span.o_field_translate').length) {
                // multi-languages activated, place the button on the left of the translation button
                this.$emojisIcon.addClass('o_mail_emojis_dropdown_translation');
            }
            if (this.$el.filter('textarea').length) {
                this.$emojisIcon.addClass('o_mail_emojis_dropdown_textarea');
            }
            this.$el.last().after(this.$emojisIcon);
        }

        if (this.mode === 'edit') {
            this.$emojisIcon.show();
        } else {
            this.$emojisIcon.hide();
        }
    }
};

export default FieldEmojiCommon;
