odoo.define('web.KeyboardNavigation', function (require) {
    "use strict";
    const { isOsMac, isBrowserChrome } = require('web.BrowserDetection');
    const { useListener } = require('web.custom_hooks');

    const { Component } = owl;
    const { useExternalListener } = owl.hooks;
    const { xml } = owl.tags;

    /**
     * list of the key that should not be used as accesskeys.
     * Either because we want to reserve them for a specific behavior in Odoo or
     * because they will not work in certain browser/OS
     */
    const knownUnusableAccessKeys = [' ',
        'A', // reserved for Odoo Edit
        'B', // reserved for Odoo Previous Breadcrumb (Back)
        'C', // reserved for Odoo Create
        'H', // reserved for Odoo Home
        'J', // reserved for Odoo Discard
        'K', // reserved for Odoo Kanban view
        'L', // reserved for Odoo List view
        'N', // reserved for Odoo pager Next
        'P', // reserved for Odoo pager Previous
        'S', // reserved for Odoo Save
        'Q', // reserved for Odoo Search
        'E', // chrome does not support 'E' access key --> go to address bar to search google
        'F', // chrome does not support 'F' access key --> go to menu
        'D', // chrome does not support 'D' access key --> go to address bar
        '0', '1', '2', '3', '4', '5', '6', '7', '8', '9' // reserved for Odoo menus
    ];

    class KeyboardNavigation extends Component {
        constructor() {
            super(...arguments);
            this._areAccessKeyVisible = false;
            useListener('keydown', this._onKeyDown);
            useListener('keyup', this._onKeyUp);
            useExternalListener(window, 'blur', this._hideAccessKeyOverlay);
            this._overlays = [];
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @private
         */
        _addAccessKeyOverlays() {
            const accesskeyElements = Array.from(document.querySelectorAll('[accesskey]'))
                .filter(x => x && !!(x.offsetWidth || x.offsetHeight || x.getClientRects().length));

            class Overlay extends Component {}
            Overlay.template = xml`<div class="o_web_accesskey_overlay" t-esc="props.accessKey"/>`;

            for (const element of accesskeyElements) {
                const overlay = new Overlay(null, {
                    accessKey: element.getAttribute('accesskey').toUpperCase(),
                });
                let overlayParent;
                if (element.tagName.toUpperCase() === 'input') {
                    // special case for the search input that has an access key
                    // defined. We cannot set the overlay on the input itself,
                    // only on its parent.
                    overlayParent = element.parentElement;
                } else {
                    overlayParent = element;
                }

                const style = window.getComputedStyle(overlayParent);
                if (style.position !== 'absolute') {
                    overlayParent.style.position = 'relative';
                }

                overlay.mount(overlayParent);
                this._overlays.push(overlay);
            }
        }
        /**
         * @private
         * @returns {string[]}
         */
        _getAllUsedAccessKeys() {
            const usedAccessKeys = knownUnusableAccessKeys.slice();
            for (const element of document.querySelectorAll('[accesskey]')) {
                usedAccessKeys.push(element.accessKey.toUpperCase());
            }
            return usedAccessKeys;
        }
        /**
         * hides the overlay that shows the access keys.
         *
         * @private
         */
        _hideAccessKeyOverlay() {
            this._areAccessKeyVisible = false;
            for (const overlay of this._overlays) {
                overlay.destroy();
            }
        }
        /**
         * @private
         */
        _setAccessKeyOnTopNavigation() {
            const menus = document.querySelectorAll('.o_menu_sections > li > a');
            for (const [ number, item ] of menus.entries()) {
                item.accessKey = number + 1;
            }
        }

        //----------------------------------------------------------------------
        // Handlers
        //----------------------------------------------------------------------

        /**
         * Assign access keys to all buttons inside $el and sets an overlay to show the access key
         * The access keys will be assigned using first the name of the button, letter by letter until we find one available,
         * after that we will assign any available letters.
         * Not all letters should be used as access keys, some of the should be reserved for standard odoo behavior or browser behavior
         *
         * @private
         * @param {KeyboardEvent} ev the keyboard event triggered
         * return {undefined|false}
         */
        _onKeyDown(ev) {
            if (document.body.classList.contains('o_ui_blocked') &&
                (ev.altKey || ev.key === 'Alt') && !ev.ctrlKey) {
                if (ev.preventDefault) {
                    ev.preventDefault();
                } else {
                    ev.returnValue = false;
                }
                if (ev.stopPropagation) {
                    ev.stopPropagation();
                }
                if (ev.cancelBubble) {
                    ev.cancelBubble = true;
                }
                return false;
            }
            if (!this._areAccessKeyVisible &&
                (ev.altKey || ev.key === 'Alt') && !ev.ctrlKey) {

                this._areAccessKeyVisible = true;
                this._setAccessKeyOnTopNavigation();
                const usedAccessKey = this._getAllUsedAccessKeys();

                const buttonsWithoutAccessKey = Array.from(document.querySelectorAll('button.btn'))
                    .filter(el =>
                        el && !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length) &&
                        !el.hasAttribute('accesskey') &&
                        !el.hasAttribute('disabled') &&
                        el.getAttribute('tabindex') !== "-1"
                    );

                for (const element of buttonsWithoutAccessKey) {
                    const buttonString = [
                        element.innerText,
                        element.title,
                        'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
                    ].join('');
                    for (const letter of buttonString) {
                        const candidateAccessKey = letter.toUpperCase();
                        if (candidateAccessKey >= 'A' && candidateAccessKey <= 'Z' &&
                            !usedAccessKey.includes(candidateAccessKey)) {
                            element.accessKey = candidateAccessKey;
                            usedAccessKey.push(candidateAccessKey);
                            break;
                        }
                    }
                }

                const elementsWithoutAriaKeyshortcut = Array
                    .from(document.querySelectorAll('[accesskey]'))
                    .filter(el => !el.hasAttribute('aria-keyshortcuts'));
                for (const element of elementsWithoutAriaKeyshortcut) {
                    element.setAttribute('aria-keyshortcuts', 'Alt+Shift+' + element.accessKey);
                }
               this._addAccessKeyOverlays();
            }
            // on mac, there are a number of keys that are only accessible though the usage of
            // the ALT key (like the @ sign in most keyboards)
            // for them we do not facilitate the access keys, so they will need to be activated classically
            // though Control + Alt + key (case sensitive), see https://developer.mozilla.org/en-US/docs/Web/HTML/Global_attributes/accesskey
            if (isOsMac) {
                return;
            }

            if (ev.altKey && !ev.ctrlKey && ev.key.length === 1) { // we don't want to catch the Alt key down, only the characters A to Z and number keys
                let elementWithAccessKey = [];
                if (ev.keyCode >= 65 && ev.keyCode <= 90 || ev.keyCode >= 97 && ev.keyCode <= 122) {
                    // 65 = A, 90 = Z, 97 = a, 122 = z
                    elementWithAccessKey = document.querySelectorAll('[accesskey="' + String.fromCharCode(ev.keyCode).toLowerCase() +
                        '"], [accesskey="' + String.fromCharCode(ev.keyCode).toUpperCase() + '"]');
                    if (elementWithAccessKey.length) {
                        if (isOsMac || !isBrowserChrome) { // on windows and linux, chrome does not prevent the default of the accesskeys
                            elementWithAccessKey[0].focus();
                            elementWithAccessKey[0].click();
                            if (ev.preventDefault) {
                                ev.preventDefault();
                            } else {
                                ev.returnValue = false;
                            }
                            if (ev.stopPropagation) {
                                ev.stopPropagation();
                            }
                            if (ev.cancelBubble) {
                                ev.cancelBubble = true;
                            }
                            return false;
                        }
                    }
                } else {
                    // identify if the user has tapped on the number keys above the text keys.
                    // this is not trivial because alt is a modifier and will not input the actual number in most keyboard layouts
                    let numberKey;
                    if (ev.code && ev.code.indexOf('Digit') === 0) {
                        //chrome & FF have the key Digit set correctly for the numbers
                        numberKey = ev.code[ev.code.length - 1];
                    } else if (ev.key && ev.key.length === 1 &&
                        ev.key >= '0' && ev.key <= '9') {
                        //edge does not use 'code' on the original event, but the 'key' is set correctly
                        numberKey = ev.key;
                    } else if (ev.keyCode >= 48 && ev.keyCode <= 57) {
                        //fallback on keyCode if both code and key are either not set or not digits
                        numberKey = ev.keyCode - 48;
                    }

                    if (numberKey >= '0' && numberKey <= '9') {
                        elementWithAccessKey = document.querySelectorAll('[accesskey="' + numberKey + '"]');
                        if (elementWithAccessKey.length) {
                            elementWithAccessKey[0].click();
                            if (ev.preventDefault) {
                                ev.preventDefault();
                            } else {
                                ev.returnValue = false;
                            }
                            if (ev.stopPropagation) {
                                ev.stopPropagation();
                            }
                            if (ev.cancelBubble) {
                                ev.cancelBubble = true;
                            }
                            return false;
                        }
                    }
                }
            }
        }
        /**
         * hides the shortcut overlays when keyup event is triggered on the ALT key
         *
         * @private
         * @param {KeyboardEvent} ev the keyboard event triggered
         * @return {undefined|false}
         */
        _onKeyUp(ev) {
            if ((ev.altKey || ev.key === 'Alt') && !ev.ctrlKey) {
                this._hideAccessKeyOverlay();
                if (ev.preventDefault) {
                    ev.preventDefault();
                } else {
                    ev.returnValue = false;
                }
                if (ev.stopPropagation) {
                    ev.stopPropagation();
                }
                if (ev.cancelBubble) {
                    ev.cancelBubble = true;
                }
                return false;
            }
        }
    }

    return KeyboardNavigation;
});

