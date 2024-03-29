/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { Toolbar } from "@web_editor/js/editor/toolbar";

patch(Toolbar.props, {
    ...Toolbar.props,
    showAnimateText: { type: Boolean, optional: true },
    showTextHighlights: { type: Boolean, optional: true },
});
patch(Toolbar.defaultProps, {
    ...Toolbar.defaultProps,
    showAnimateText: false,
    showTextHighlights: false,
});
