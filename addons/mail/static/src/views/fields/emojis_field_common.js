/** @odoo-module **/

import MailEmojisMixin from '@mail/js/emojis_mixin';

const _onEmojiClickMixin = MailEmojisMixin.onEmojiClick;
const { useRef, onMounted } = owl;

/*
 * Common code for EmojisTextField and EmojisCharField
 */
export const EmojisFieldCommon = {
    _setupOverride() {
        this.targetReadonlyElement = useRef('targetReadonlyElement');
        this.emojisDropdown = useRef('emojisDropdown');
        if (this.props.readonly) {
            onMounted(() => {
                this.targetReadonlyElement.el.innerHTML = this._formatText(this.targetReadonlyElement.el.textContent);
            });
        }
        this.onEmojiClick = this._onEmojiClick.bind(this);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _onEmojiClick() {
        _onEmojiClickMixin.apply(this, arguments);
        this.props.update(this._getTargetTextElement().value);
    },
    /**
     * Used by MailEmojisMixin, check its document for more info.
     *
     * @private
     */
    _getTargetTextElement() {
        return this.props.readonly ? this.targetReadonlyElement.el : this.targetEditElement.el;
    },
};
