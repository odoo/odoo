/** @odoo-module **/

    /**
     * Field Test Utils
     *
     * This module defines various utility functions to help testing field widgets.
     *
     * Note that all methods defined in this module are exported in the main
     * testUtils file.
     */

    import testUtilsDom from "@web/../tests/legacy/helpers/test_utils_dom";

    const ARROW_KEYS_MAPPING = {
        down: 'ArrowDown',
        left: 'ArrowLeft',
        right: 'ArrowRight',
        up: 'ArrowUp',
    };

    //-------------------------------------------------------------------------
    // Public functions
    //-------------------------------------------------------------------------

    /**
     * Sets the value of an element and then, trigger all specified events.
     * Note that this helper also checks the unicity of the target.
     *
     * Example:
     *     testUtils.fields.editAndTrigger($('selector'), 'test', ['input', 'change']);
     *
     * @param {jQuery|EventTarget} el should target an input, textarea or select
     * @param {string|number} value
     * @param {string[]} events
     * @returns {Promise}
     */
    export async function editAndTrigger(el, value, events) {
        if (el instanceof jQuery) {
            if (el.length !== 1) {
                throw new Error(`target ${el.selector} has length ${el.length} instead of 1`);
            }
            el.val(value);
        } else {
            el.value = value;
        }
        return testUtilsDom.triggerEvents(el, events);
    }

    /**
     * Sets the value of an input.
     *
     * Note that this helper also checks the unicity of the target.
     *
     * Example:
     *     testUtils.fields.editInput($('selector'), 'somevalue');
     *
     * @param {jQuery|EventTarget} el should target an input, textarea or select
     * @param {string|number} value
     * @returns {Promise}
     */
    export async function editInput(el, value) {
        return editAndTrigger(el, value, ['input']);
    }

    /**
     * Helper to trigger a key event on an element.
     *
     * @param {string} type type of key event ('press', 'up' or 'down')
     * @param {jQuery} $el
     * @param {number|string} keyCode used as number, but if string, it'll check if
     *   the string corresponds to a key -otherwise it will keep only the first
     *   char to get a letter key- and convert it into a keyCode.
     * @returns {Promise}
     */
    function triggerKey(type, $el, keyCode) {
        type = 'key' + type;
        const params = {};
        if (typeof keyCode === 'string') {
            // Key (new API)
            if (keyCode in ARROW_KEYS_MAPPING) {
                params.key = ARROW_KEYS_MAPPING[keyCode];
            } else {
                params.key = keyCode[0].toUpperCase() + keyCode.slice(1).toLowerCase();
            }
            // KeyCode/which (jQuery)
            if (keyCode.length > 1) {
                keyCode = keyCode.toUpperCase();
                keyCode = $.ui.keyCode[keyCode];
            } else {
                keyCode = keyCode.charCodeAt(0);
            }
        }
        params.keyCode = keyCode;
        params.which = keyCode;
        return testUtilsDom.triggerEvent($el, type, params);
    }

    /**
     * Helper to trigger a keydown event on an element.
     *
     * @param {jQuery} $el
     * @param {number|string} keyCode @see triggerKey
     * @returns {Promise}
     */
    function triggerKeydown($el, keyCode) {
        return triggerKey('down', $el, keyCode);
    }

    export default {
        editAndTrigger,
        editInput,
        triggerKeydown,
    };
