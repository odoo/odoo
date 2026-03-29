odoo.define('web.KeyboardNavigationMixin', function (require) {
    "use strict";
    var BrowserDetection = require('web.BrowserDetection');
    const core = require('web.core');

    /**
     * list of the key that should not be used as accesskeys. Either because we want to reserve them for a specific behavior in Odoo or
     * because they will not work in certain browser/OS
     */
    var knownUnusableAccessKeys = [' ',
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

    var KeyboardNavigationMixin = {
        events: {
            'keydown': '_onKeyDown',
            'keyup': '_onKeyUp',
        },

        /**
         * @constructor
         * @param {object} [options]
         * @param {boolean} [options.autoAccessKeys=true]
         *      Whether accesskeys should be created automatically for buttons
         *      without them in the page.
         * @param {boolean} [options.skipRenderOverlay=false]
         *      Whether the accesskeys overlay rendering must be skipped.
         */
        init: function (options) {
            this.options = Object.assign({
                autoAccessKeys: true,
                skipRenderOverlay: false,
            }, options);
            this._areAccessKeyVisible = false;
            this.BrowserDetection = new BrowserDetection();
        },
        /**
         * @override
         */
        start: function () {
            const temp = this._hideAccessKeyOverlay.bind(this);
            this._hideAccessKeyOverlay = () => temp();
            window.addEventListener('blur', this._hideAccessKeyOverlay);
            core.bus.on('click', null, this._hideAccessKeyOverlay);
        },
        /**
         * @destructor
         */
        destroy: function () {
            window.removeEventListener('blur', this._hideAccessKeyOverlay);
            core.bus.off('click', null, this._hideAccessKeyOverlay);
        },

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        /**
         * @private
         */
        _addAccessKeyOverlays: function () {
            if (this.options.skipRenderOverlay) {
                return;
            }
            var accesskeyElements = $(document).find('[accesskey]').filter(':visible');
            _.each(accesskeyElements, function (elem) {
                var overlay = $(_.str.sprintf("<div class='o_web_accesskey_overlay'>%s</div>", $(elem).attr('accesskey').toUpperCase()));

                var $overlayParent;
                if (elem.tagName.toUpperCase() === "INPUT") {
                    // special case for the search input that has an access key
                    // defined. We cannot set the overlay on the input itself,
                    // only on its parent.
                    $overlayParent = $(elem).parent();
                } else {
                    $overlayParent = $(elem);
                }

                if ($overlayParent.css('position') !== 'absolute') {
                    $overlayParent.css('position', 'relative');
                }
                overlay.appendTo($overlayParent);
            });
        },
        /**
         * @private
         * @return {jQuery[]}
         */
        _getAllUsedAccessKeys: function () {
            var usedAccessKeys = knownUnusableAccessKeys.slice();
            this.$el.find('[accesskey]').each(function (_, elem) {
                usedAccessKeys.push(elem.accessKey.toUpperCase());
            });
            return usedAccessKeys;
        },
        /**
         * hides the overlay that shows the access keys.
         *
         * @private
         * @param $parent {jQueryElemen} the parent of the DOM element to which shorcuts overlay have been added
         * @return {undefined|jQuery}
         */
        _hideAccessKeyOverlay: function () {
            this._areAccessKeyVisible = false;
            var overlays = this.$el.find('.o_web_accesskey_overlay');
            if (overlays.length) {
                return overlays.remove();
            }
        },
        /**
         * @private
         */
        _setAccessKeyOnTopNavigation: function () {
            this.$el.find('.o_menu_sections>li>a').each(function (number, item) {
                item.accessKey = number + 1;
            });
        },

        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------

        /**
         * Assign access keys to all buttons inside $el and sets an overlay to show the access key
         * The access keys will be assigned using first the name of the button, letter by letter until we find one available,
         * after that we will assign any available letters.
         * Not all letters should be used as access keys, some of the should be reserved for standard odoo behavior or browser behavior
         *
         * @private
         * @param keyDownEvent {jQueryKeyboardEvent} the keyboard event triggered
         * return {undefined|false}
         */
        _onKeyDown: function (keyDownEvent) {
            if ($('body.o_ui_blocked').length &&
            (keyDownEvent.altKey || keyDownEvent.key === 'Alt') &&
            !keyDownEvent.ctrlKey) {
                if (keyDownEvent.preventDefault) keyDownEvent.preventDefault(); else keyDownEvent.returnValue = false;
                if (keyDownEvent.stopPropagation) keyDownEvent.stopPropagation();
                if (keyDownEvent.cancelBubble) keyDownEvent.cancelBubble = true;
                return false;
            }
            if (!this._areAccessKeyVisible &&
                (keyDownEvent.altKey || keyDownEvent.key === 'Alt') &&
                !keyDownEvent.ctrlKey) {

                this._areAccessKeyVisible = true;

                this._setAccessKeyOnTopNavigation();

                var usedAccessKey = this._getAllUsedAccessKeys();

                if (this.options.autoAccessKeys) {
                    var buttonsWithoutAccessKey = this.$el.find('button.btn:visible')
                        .not('[accesskey]')
                        .not('[disabled]')
                        .not('[tabindex="-1"]');
                    _.each(buttonsWithoutAccessKey, function (elem) {
                        var buttonString = [elem.innerText, elem.title, "ABCDEFGHIJKLMNOPQRSTUVWXYZ"].join('');
                        for (var letterIndex = 0; letterIndex < buttonString.length; letterIndex++) {
                            var candidateAccessKey = buttonString[letterIndex].toUpperCase();
                            if (candidateAccessKey >= 'A' && candidateAccessKey <= 'Z' &&
                                !_.includes(usedAccessKey, candidateAccessKey)) {
                                elem.accessKey = candidateAccessKey;
                                usedAccessKey.push(candidateAccessKey);
                                break;
                            }
                        }
                    });
                }

                var elementsWithoutAriaKeyshortcut = this.$el.find('[accesskey]').not('[aria-keyshortcuts]');
                _.each(elementsWithoutAriaKeyshortcut, function (elem) {
                    elem.setAttribute('aria-keyshortcuts', 'Alt+Shift+' + elem.accessKey);
                });
                this._addAccessKeyOverlays();
            }
            // on mac, there are a number of keys that are only accessible though the usage of
            // the ALT key (like the @ sign in most keyboards)
            // for them we do not facilitate the access keys, so they will need to be activated classically
            // though Control + Alt + key (case sensitive), see https://developer.mozilla.org/en-US/docs/Web/HTML/Global_attributes/accesskey
            if (this.BrowserDetection.isOsMac())
                return;

            if (keyDownEvent.altKey && !keyDownEvent.ctrlKey && keyDownEvent.key.length === 1) { // we don't want to catch the Alt key down, only the characters A to Z and number keys
                var elementWithAccessKey = [];
                if (keyDownEvent.keyCode >= 65 && keyDownEvent.keyCode <= 90 || keyDownEvent.keyCode >= 97 && keyDownEvent.keyCode <= 122) {
                    // 65 = A, 90 = Z, 97 = a, 122 = z
                    elementWithAccessKey = document.querySelectorAll('[accesskey="' + String.fromCharCode(keyDownEvent.keyCode).toLowerCase() +
                        '"], [accesskey="' + String.fromCharCode(keyDownEvent.keyCode).toUpperCase() + '"]');
                    if (elementWithAccessKey.length) {
                        if (this.BrowserDetection.isOsMac() ||
                            !this.BrowserDetection.isBrowserChrome()) { // on windows and linux, chrome does not prevent the default of the accesskeys
                            elementWithAccessKey[0].focus();
                            elementWithAccessKey[0].click();
                            if (keyDownEvent.preventDefault) keyDownEvent.preventDefault(); else keyDownEvent.returnValue = false;
                            if (keyDownEvent.stopPropagation) keyDownEvent.stopPropagation();
                            if (keyDownEvent.cancelBubble) keyDownEvent.cancelBubble = true;
                            return false;
                        }
                    }
                }
                else {
                    // identify if the user has tapped on the number keys above the text keys.
                    // this is not trivial because alt is a modifier and will not input the actual number in most keyboard layouts
                    var numberKey;
                    if (keyDownEvent.originalEvent.code && keyDownEvent.originalEvent.code.indexOf('Digit') === 0) {
                        //chrome & FF have the key Digit set correctly for the numbers
                        numberKey = keyDownEvent.originalEvent.code[keyDownEvent.originalEvent.code.length - 1];
                    } else if (keyDownEvent.originalEvent.key &&
                        keyDownEvent.originalEvent.key.length === 1 &&
                        keyDownEvent.originalEvent.key >= '0' &&
                        keyDownEvent.originalEvent.key <= '9') {
                        //edge does not use 'code' on the original event, but the 'key' is set correctly
                        numberKey = keyDownEvent.originalEvent.key;
                    } else if (keyDownEvent.keyCode >= 48 && keyDownEvent.keyCode <= 57) {
                        //fallback on keyCode if both code and key are either not set or not digits
                        numberKey = keyDownEvent.keyCode - 48;
                    }

                    if (numberKey >= '0' && numberKey <= '9') {
                        elementWithAccessKey = document.querySelectorAll('[accesskey="' + numberKey + '"]');
                        if (elementWithAccessKey.length) {
                            elementWithAccessKey[0].click();
                            if (keyDownEvent.preventDefault) keyDownEvent.preventDefault(); else keyDownEvent.returnValue = false;
                            if (keyDownEvent.stopPropagation) keyDownEvent.stopPropagation();
                            if (keyDownEvent.cancelBubble) keyDownEvent.cancelBubble = true;
                            return false;
                        }
                    }
                }
            }
        },
        /**
         * hides the shortcut overlays when keyup event is triggered on the ALT key
         *
         * @private
         * @param keyUpEvent {jQueryKeyboardEvent} the keyboard event triggered
         * @return {undefined|false}
         */
        _onKeyUp: function (keyUpEvent) {
            if ((keyUpEvent.altKey || keyUpEvent.key === 'Alt') && !keyUpEvent.ctrlKey) {
                if (this.options.skipRenderOverlay) {
                    return;
                }
                this._hideAccessKeyOverlay();
                if (keyUpEvent.preventDefault) keyUpEvent.preventDefault(); else keyUpEvent.returnValue = false;
                if (keyUpEvent.stopPropagation) keyUpEvent.stopPropagation();
                if (keyUpEvent.cancelBubble) keyUpEvent.cancelBubble = true;
                return false;
            }
        },
    };

    return KeyboardNavigationMixin;

});
