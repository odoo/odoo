// @ts-check

/** @odoo-module alias=@web/../tests/legacy_tests/helpers/test_utils_fields default=false */

    /**
     * Field Test Utils
     *
     * This module defines various utility functions to help testing field widgets.
     *
     * Note that all methods defined in this module are exported in the main
     * testUtils file.
     */

    import testUtilsDom from "./test_utils_dom";

    //-------------------------------------------------------------------------
    // Public functions
    //-------------------------------------------------------------------------

    /**
     * Sets the value of an element and then, trigger all specified events.
     * Note that this helper also checks the unicity of the target.
     *
     * Example:
     *     testUtils.fields.editAndTrigger(el, 'test', ['input', 'change']);
     *
     * @param {EventTarget} el should target an input, textarea or select
     * @param {string|number} value
     * @param {string[]} events
     * @returns {Promise}
     */
    export async function editAndTrigger(el, value, events) {
        el.value = value;
        return testUtilsDom.triggerEvents(el, events);
    }

    /**
     * Sets the value of an input.
     *
     * Note that this helper also checks the unicity of the target.
     *
     * Example:
     *     testUtils.fields.editInput(el, 'somevalue');
     *
     * @param {EventTarget} el should target an input, textarea or select
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
     * @param {EventTarget} el
     * @param {string} key
     * @returns {Promise}
     */
    function triggerKey(type, el, key) {
        type = 'key' + type;
        const params = {};
        params.key = key;
        return testUtilsDom.triggerEvent(el, type, params);
    }

    /**
     * Helper to trigger a keydown event on an element.
     *
     * @param {EventTarget} el
     * @param {number|string} key @see triggerKey
     * @returns {Promise}
     */
    function triggerKeydown(el, key) {
        return triggerKey('down', el, key);
    }

    export default {
        editAndTrigger,
        editInput,
        triggerKeydown,
    };
