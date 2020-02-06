odoo.define('mail.messaging.component.PopoverButton', function (require) {
'use strict';

const { Component, useState } = owl;

class PopoverButton extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        this.state = useState({
            /**
             * Determine whether the popover is open or not.
             */
            isOpen: false,
        });
        /**
         * jQuery node reference of the popover.
         */
        this._$popover = undefined;
        /**
         * Popover id obtained from 'aria-describedby'. Useful to cleanly
         * destroy the popover (prevents issue in which the popover is never
         * destroyed when it is shown and a re-render is triggered).
         */
        this._popoverId = undefined;
        this._onClickCaptureGlobal = this._onClickCaptureGlobal.bind(this);
    }

    mounted() {
        const self = this;
        const popoverParams = {
            boundary: this.props.boundary,
            content() {
                self._popoverId = this.getAttribute('aria-describedby');
                return self._getPopoverContent();
            },
            html: this.props.isHtml,
            offset: this.props.offset,
            placement: this.props.placement,
            trigger: this.props.trigger,
            animation: !this.env.disableAnimation,
        };
        if (this.props.popoverTitle) {
            popoverParams.title = this.props.popoverTitle;
        }
        this._$popover = $(this.el).popover(popoverParams);
        document.addEventListener('click', this._onClickCaptureGlobal, true);
    }

    willUnmount() {
        this._hidePopover();
        document.removeEventListener('click', this._onClickCaptureGlobal, true);
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @param {EventTarget} target
     * @returns {boolean}
     */
    isInsideEventTarget(target) {
        return target === this.el || target.closest(`#${this._popoverId}`);
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * To be overriden by subcomponents.
     * Called by the bootstrap popover helper to determine the content of the popover.
     *
     * @private
     */
    _getPopoverContent(){}

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

}

Object.assign(PopoverButton, {
    defaultProps: {
        boundary: 'viewport',
        isHtml: true,
        offset: '0, 1',
        placement: 'right',
        trigger: 'click',
    },
    props: {
        buttonText: {
            type: String,
            optional: true,
        },
        boundary: String,
        isHtml: Boolean,
        offset: String,
        placement: String,
        popoverTitle: {
            type: String,
            optional: true,
        },
        trigger: String,
    },
    template: 'mail.messaging.component.PopoverButton',
});

return PopoverButton;

});
