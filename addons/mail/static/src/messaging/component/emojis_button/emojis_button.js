odoo.define('mail.messaging.component.EmojisButton', function (require) {
'use strict';

const components = {
    EmojisPopover: require('mail.messaging.component.EmojisPopover'),
    PopoverButtonWithComponent: require('mail.messaging.component.PopoverButtonWithComponent'),
};

class EmojisButton extends components.PopoverButtonWithComponent {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        this._onEmojiSelection = this._onEmojiSelection.bind(this);
    }

    /**
     * @override
     */
    async mounted() {
        await super.mounted();
        this._popoverComponent.el.addEventListener('o-emoji-selection', this._onEmojiSelection);
    }

    /**
     * @override
     */
    willUnmount() {
        if (this._popoverComponent.el) {
            this._popoverComponent.el.removeEventListener('o-emoji-selection', this._onEmojiSelection);
        }
        super.willUnmount();
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @returns {EmojisPopover}
     */
    _createPopoverComponent() {
        const EmojisPopoverComponent = components.EmojisPopover;
        EmojisPopoverComponent.env = this.env;
        return new EmojisPopoverComponent(null);
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {CustomEvent} ev
     * @param {Object} ev.detail
     * @param {string} ev.detail.unicode
     */
    _onEmojiSelection(ev) {
        this._hidePopover();
        this.trigger('o-emoji-selection', {
            unicode: ev.detail.unicode,
        });
    }

}

return EmojisButton;

});
