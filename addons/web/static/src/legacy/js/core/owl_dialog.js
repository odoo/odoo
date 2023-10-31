odoo.define('web.OwlDialog', function (require) {
    "use strict";

    const { Component, hooks, misc } = owl;
    const { Portal } = misc;
    const { useRef } = hooks;
    const SIZE_CLASSES = {
        'extra-large': 'modal-xl',
        'large': 'modal-lg',
        'small': 'modal-sm',
    };

    /**
     * Dialog (owl version)
     *
     * Represents a bootstrap-styled dialog handled with pure JS. Its implementation
     * is roughly the same as the legacy dialog, the only exception being the buttons.
     * @extends Component
     **/
    class Dialog extends Component {
        /**
         * @param {Object} [props]
         * @param {(boolean|string)} [props.backdrop='static'] The kind of modal backdrop
         *      to use (see Bootstrap documentation).
         * @param {string} [props.contentClass] Class to add to the dialog
         * @param {boolean} [props.fullscreen=false] Whether the dialog should be
         *      open in fullscreen mode (the main usecase is mobile).
         * @param {boolean} [props.renderFooter=true] Whether the dialog footer
         *      should be rendered.
         * @param {boolean} [props.renderHeader=true] Whether the dialog header
         *      should be rendered.
         * @param {string} [props.size='large'] 'extra-large', 'large', 'medium'
         *      or 'small'.
         * @param {string} [props.stopClicks=true] whether the dialog should stop
         *      the clicks propagation outside of itself.
         * @param {string} [props.subtitle='']
         * @param {string} [props.title='Odoo']
         * @param {boolean} [props.technical=true] If set to false, the modal will have
         *      the standard frontend style (use this for non-editor frontend features).
         */
        constructor() {
            super(...arguments);

            this.modalRef = useRef('modal');
            this.footerRef = useRef('modal-footer');
        }

        mounted() {
            this.constructor.display(this);

            this.env.bus.on('close_dialogs', this, this._close);

            if (this.props.renderFooter) {
                // Set up main button : will first look for an element with the
                // 'btn-primary' class, then a 'btn' class, then the first button
                // element.
                let mainButton = this.footerRef.el.querySelector('.btn.btn-primary');
                if (!mainButton) {
                    mainButton = this.footerRef.el.querySelector('.btn');
                }
                if (!mainButton) {
                    mainButton = this.footerRef.el.querySelector('button');
                }
                if (mainButton) {
                    this.mainButton = mainButton;
                    this.mainButton.addEventListener('keydown', this._onMainButtonKeydown.bind(this));
                    this.mainButton.focus();
                }
            }

            this._removeTooltips();

            // Notifies new webclient to adjust UI active element
            this.env.bus.trigger("owl_dialog_mounted", this);
        }

        willUnmount() {
            // Notifies new webclient to adjust UI active element
            this.env.bus.trigger("owl_dialog_willunmount", this);

            this.env.bus.off('close_dialogs', this, this._close);

            this._removeTooltips();

            this.constructor.hide(this);
        }

        //--------------------------------------------------------------------------
        // Getters
        //--------------------------------------------------------------------------

        /**
         * @returns {string}
         */
        get size() {
            return SIZE_CLASSES[this.props.size];
        }

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        /**
         * Send an event signaling that the dialog must be closed.
         * @private
         */
        _close() {
            this.trigger('dialog-closed');
        }

        /**
         * Remove any existing tooltip present in the DOM.
         * @private
         */
        _removeTooltips() {
            for (const tooltip of document.querySelectorAll('.tooltip')) {
                tooltip.remove(); // remove open tooltip if any to prevent them staying when modal is opened
            }
        }

        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------

        /**
         * @private
         * @param {MouseEvent} ev
         */
        _onBackdropClick(ev) {
            if (!this.props.backdrop || ev.target !== ev.currentTarget) {
                return;
            }
            if (this.props.backdrop === 'static') {
                if (this.mainButton) {
                    this.mainButton.focus();
                }
            } else {
                this._close();
            }
        }

        /**
         * @private
         * @param {MouseEvent} ev
         */
        _onClick(ev) {
            if (this.props.stopClicks) {
                ev.stopPropagation();
            }
        }

        /**
         * @private
         */
        _onFocus() {
            if (this.mainButton) {
                this.mainButton.focus();
            }
        }

        /**
         * Manage the TAB key on the main button. If the focus is on a primary
         * button and the user tries to tab to go to the next button : a tooltip
         * will be displayed.
         * @private
         * @param {KeyboardEvent} ev
         */
        _onMainButtonKeydown(ev) {
            if (ev.key === 'Tab' && !ev.shiftKey) {
                ev.preventDefault();
                $(this.mainButton)
                    .tooltip({
                        delay: { show: 200, hide: 0 },
                        title: () => this.env.qweb.renderToString('web.DialogButton.tooltip', {
                            title: this.mainButton.innerText.toUpperCase(),
                        }),
                        trigger: 'manual',
                    })
                    .tooltip('show');
            }
        }

        //--------------------------------------------------------------------------
        // Static
        //--------------------------------------------------------------------------

        /**
         * Push the given dialog at the end of the displayed list then set it as
         * active and all the others as passive.
         * @param {(LegacyDialog|OwlDialog|LegacyAdaptedDialog)} dialog
         */
        static display(dialog) {
            const activeDialog = this.displayed[this.displayed.length - 1];
            if (activeDialog) {
                // Deactivate previous dialog
                const activeDialogEl = activeDialog.modalRef ?
                    // Owl dialog | LegacyAdaptedDialog
                    activeDialog.modalRef.el :
                    // Legacy dialog
                    activeDialog.$modal[0];
                activeDialogEl.classList.add('o_inactive_modal');
                activeDialogEl.removeAttribute("tabindex");
            }
            // Push dialog
            this.displayed.push(dialog);
            // Update body class
            document.body.classList.add('modal-open');
        }

        /**
         * Set the given displayed dialog as passive and the last added displayed dialog
         * as active, then remove it from the displayed list.
         * @param {(LegacyDialog|OwlDialog|LegacyAdaptedDialog)} dialog
         */
        static hide(dialog) {
            // Remove given dialog from the list
            this.displayed.splice(this.displayed.indexOf(dialog), 1);
            // Activate last dialog and update body class
            const lastDialog = this.displayed[this.displayed.length - 1];
            if (lastDialog) {
                lastDialog.el.focus();
                const modalEl = lastDialog.modalRef ?
                    // Owl dialog | LegacyAdaptedDialog
                    lastDialog.modalRef.el :
                    // Legacy dialog
                    lastDialog.$modal[0];
                modalEl.classList.remove('o_inactive_modal');
                modalEl.setAttribute("tabindex", "-1");
            } else {
                document.body.classList.remove('modal-open');
            }
        }
    }

    Dialog.displayed = [];

    Dialog.components = { Portal };
    Dialog.defaultProps = {
        backdrop: 'static',
        renderFooter: true,
        renderHeader: true,
        size: 'large',
        stopClicks: true,
        technical: true,
        title: "Odoo",
    };
    Dialog.props = {
        backdrop: { validate: b => ['static', true, false].includes(b) },
        contentClass: { type: String, optional: 1 },
        fullscreen: { type: Boolean, optional: 1 },
        renderFooter: Boolean,
        renderHeader: Boolean,
        size: { validate: s => ['extra-large', 'large', 'medium', 'small'].includes(s) },
        stopClicks: Boolean,
        subtitle: { type: String, optional: 1 },
        technical: Boolean,
        title: String,
    };
    Dialog.template = 'web.OwlDialog';

    return Dialog;
});
