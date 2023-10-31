odoo.define('web.DropdownMenuItem', function (require) {
    "use strict";

    const { useListener } = require('web.custom_hooks');

    const { Component, hooks } = owl;
    const { useExternalListener, useRef, useState } = hooks;

    /**
     * Dropdown menu item
     *
     * Generic component instantiated by a dropdown menu (@see DropdownMenu) in
     * the absence of `Component` and `props` keys in a given item object.
     *
     * In its simplest form, a dropdown menu item will be given a description (optional,
     * but highly recommended) and will trigger a 'select-item' when clicked on.
     * Additionaly it can receive the following props:
     * - isActive: will add a `checked` symbol on the left side of the item
     * - removable: will add a `remove` trash icon on the right side of the item.
     *              when clicked, will trigger a 'remove-item' event.
     * - options: will change the behaviour of the item ; instead of triggering
     *            an event, the item will act as a nested dropdown menu and display
     *            its given options. These will have the same definition as another
     *            dropdown item but cannot have options of their own.
     *
     * It is recommended to extend this class when defining a Component which will
     * be put inside of a dropdown menu (@see CustomFilterItem as example).
     * @extends Component
     */
    class DropdownMenuItem extends Component {
        constructor() {
            super(...arguments);

            this.canBeOpened = Boolean(this.props.options && this.props.options.length);

            this.fallbackFocusRef = useRef('fallback-focus');
            this.state = useState({ open: false });

            useExternalListener(window, 'click', this._onWindowClick);
            useListener('keydown', this._onKeydown);
        }

        //---------------------------------------------------------------------
        // Handlers
        //---------------------------------------------------------------------

        /**
         * @private
         * @param {KeyboardEvent} ev
         */
        _onKeydown(ev) {
            if (['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName)) {
                return;
            }
            switch (ev.key) {
                case 'ArrowLeft':
                    if (this.canBeOpened && this.state.open) {
                        ev.preventDefault();
                        if (this.fallbackFocusRef.el) {
                            this.fallbackFocusRef.el.focus();
                        }
                        this.state.open = false;
                    }
                    break;
                case 'ArrowRight':
                    if (this.canBeOpened && !this.state.open) {
                        ev.preventDefault();
                        this.state.open = true;
                    }
                    break;
                case 'Escape':
                    ev.target.blur();
                    if (this.canBeOpened && this.state.open) {
                        ev.preventDefault();
                        ev.stopPropagation();
                        if (this.fallbackFocusRef.el) {
                            this.fallbackFocusRef.el.focus();
                        }
                        this.state.open = false;
                    }
            }
        }

        /**
         * @private
         * @param {MouseEvent} ev
         */
        _onWindowClick(ev) {
            if (
                this.state.open &&
                !this.el.contains(ev.target) &&
                !this.el.contains(document.activeElement)
            ) {
                this.state.open = false;
            }
        }
    }

    DropdownMenuItem.template = 'web.DropdownMenuItem';

    return DropdownMenuItem;
});
