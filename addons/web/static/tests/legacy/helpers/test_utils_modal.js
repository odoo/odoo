/** @odoo-module alias=web.test_utils_modal **/

    /**
     * Modal Test Utils
     *
     * This module defines various utility functions to help test pivot views.
     *
     * Note that all methods defined in this module are exported in the main
     * testUtils file.
     */

    import { _t } from "@web/core/l10n/translation";
    import testUtilsDom from "web.test_utils_dom";

    /**
     * Click on a button in the footer of a modal (which contains a given string).
     *
     * @param {string} text (in english: this method will perform the translation)
     */
    function clickButton(text) {
        return testUtilsDom.click($(`.modal-footer button:contains(${_t(text)})`));
    }

    export default { clickButton };
