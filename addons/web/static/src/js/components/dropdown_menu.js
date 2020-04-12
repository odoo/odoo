odoo.define('web.DropdownMenu', function (require) {
    "use strict";

    const DropdownMenuItem = require('web.DropdownMenuItem');

    const { Component, hooks } = owl;
    const { useExternalListener, useRef, useState } = hooks;

    /**
     * Dropdown menu
     *
     * Generic component used to generate a list of interactive items. It uses some
     * bootstrap classes but most interactions are handled in here or in the dropdown
     * menu item class definition, including some keyboard navigation and escaping
     * system (click outside to close the dropdown).
     *
     * The layout of a dropdown menu is as following:
     * > a Button (always rendered) with a `title` and an optional `icon`;
     * > a Dropdown (rendered when open) containing a collection of given items.
     *   These items must be objects and can have two shapes:
     *   1. item.Component & item.props > will instantiate the given Component with
     *      the given props. Any additional key will be useless.
     *   2. any other shape > will instantiate a DropdownMenuItem with the item
     *      object being its props. There is no props validation as this object
     *      will be passed as-is when `selected` and can contain additional meta-keys
     *      that will not affect the displayed item. For more information regarding
     *      the behaviour of these items, @see DropdownMenuItem.
     * @extends Component
     */
    class DropdownMenu extends Component {
        constructor() {
            super(...arguments);

            this.dropdownMenu = useRef('dropdown');
            this.state = useState({ open: false });

            this.symbol = this.env.device.isMobile ? 'fa fa-chevron-right float-right mt4' : false;

            useExternalListener(window, 'click', this._onWindowClick);
            useExternalListener(window, 'keydown', this._onWindowKeydown);
        }

        //---------------------------------------------------------------------
        // Getters
        //---------------------------------------------------------------------

        /**
         * Overriden in case we want to keep the caret style on the button in mobile.
         * @returns {boolean}
         */
        get displayCaret() {
            return !this.env.device.isMobile;
        }

        /**
         * Meant to be overriden to provide the list of items to display.
         * @returns {Object[]}
         */
        get items() {
            return this.props.items;
        }

        /**
         * @returns {string}
         */
        get title() {
            return this.props.title;
        }

        //---------------------------------------------------------------------
        // Handlers
        //---------------------------------------------------------------------

        /**
         * @private
         * @param {KeyboardEvent} ev
         */
        _onButtonKeydown(ev) {
            switch (ev.key) {
                case 'ArrowLeft':
                case 'ArrowRight':
                case 'ArrowUp':
                case 'ArrowDown':
                    const firstItem = this.el.querySelector('.dropdown-item');
                    if (firstItem) {
                        ev.preventDefault();
                        firstItem.focus();
                    }
            }
        }

        /**
         * @private
         * @param {OwlEvent} ev
         */
        _onItemSelected(ev) { }

        /**
         * @private
         * @param {MouseEvent} ev
         */
        _onWindowClick(ev) {
            if (this.state.open && !this.el.contains(ev.target)) {
                this.state.open = false;
            }
        }

        /**
         * @private
         * @param {KeyboardEvent} ev
         */
        _onWindowKeydown(ev) {
            if (this.state.open && ev.key === 'Escape') {
                this.state.open = false;
            }
        }
    }

    DropdownMenu.components = { DropdownMenuItem };
    DropdownMenu.defaultProps = { items: [] };
    DropdownMenu.props = {
        icon: { type: String, optional: 1 },
        items: {
            type: Array,
            element: Object,
            optional: 1,
        },
        title: { type: String, optional: 1 },
    };
    DropdownMenu.template = 'web.DropdownMenu';

    return DropdownMenu;
});
