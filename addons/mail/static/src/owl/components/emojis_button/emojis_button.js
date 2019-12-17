odoo.define('mail.component.EmojisButton', function (require) {
'use strict';

const Popover = require('mail.component.EmojisPopover');

const { Component, useState } = owl;

class EmojisButton extends Component {

    /**
     * @param {...any} args
     */
    constructor(...args) {
        super(...args);
        this.state = useState({
            /**
             * Determine whether the emoji popover button is open or not.
             */
            isOpen: false,
        });
        /**
         * jQuery node reference of the popover.
         */
        this._$popover = undefined;
        /**
         * Node reference of the popover component.
         */
        this._popover = undefined;
        /**
         * Popover id obtainned from 'aria-describedby'. Useful to cleanly
         * destroy the popover (prevents issue in which the popover is never
         * destroyed when it is shown and a re-render is triggered).
         */
        this._popoverId = undefined;
        this._onClickCaptureGlobal = this._onClickCaptureGlobal.bind(this);
    }

    async mounted() {
        const self = this;
        Popover.env = this.env;
        this._popover = new Popover(null);
        await this._popover.mount(document.createElement('div'));
        if (this.__owl__.isDestroyed) {
            return;
        }
        this._popover.el.outerHTML = this._popover.el;
        this._$popover = $(this.el).popover({
            boundary: 'viewport',
            content() {
                const $this = $(this);
                self._popoverId = $this.attr('aria-describedby');
                self._popover.__owl__.isMounted = true;
                return self._popover.el;
            },
            html: true,
            offset: '0, 1',
            placement: 'top',
            trigger: 'click',
            animation: !this.env.disableAnimation,
        });
        this._popover.el.addEventListener('o-emoji-selection', ev => this._onEmojiSelection(ev));
        document.addEventListener('click', this._onClickCaptureGlobal, true);
    }

    willUnmount() {
        this._hidePopover();
        this._popover.__owl__.isMounted = false;
        this._popover.destroy();
        document.removeEventListener('click', this._onClickCaptureGlobal, true);
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @param {EventTarget} target
     * @return {boolean}
     */
    isInsideEventTarget(target) {
        return target === this.el || target.closest(`#${this._popoverId}`);
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _hidePopover() {
        if (this._$popover) {
            this._$popover.popover('hide');
        }
        this._popoverId = undefined;
        this.state.isOpen = false;
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickCaptureGlobal(ev) {
        if (ev.target === this.el) {
            this.state.isOpen = !this.state.isOpen;
            return;
        }
        if (!this._popoverId) {
            return;
        }
        if (ev.target.closest(`#${this._popoverId}`)) {
            this.state.isOpen = true;
            return;
        }
        this._hidePopover();
    }

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

EmojisButton.template = 'mail.component.EmojisButton';

return EmojisButton;

});
