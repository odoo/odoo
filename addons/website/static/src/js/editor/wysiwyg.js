/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { Wysiwyg } from "@web_editor/js/wysiwyg/wysiwyg";

patch(Wysiwyg.prototype, {
    /**
     * Add selector for the autocomplete to delay blur
     *
     * @override
     */
    _getDelayBlurSelectors() {
        return super._getDelayBlurSelectors().concat([".ui-autocomplete"]);
    },
});
