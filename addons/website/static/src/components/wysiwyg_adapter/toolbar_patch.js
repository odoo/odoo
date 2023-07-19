/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { Toolbar } from "@web_editor/js/editor/toolbar";

patch(Toolbar.props, 'toolbar_patch.js', {
    ...Toolbar.props,
    showAnimateText: { type: Boolean, optional: true },
});
patch(Toolbar.defaultProps, 'toolbar_patch.js', {
    ...Toolbar.defaultProps,
    showAnimateText: false,
});
