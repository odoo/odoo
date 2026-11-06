/** @odoo-module */

import {ViewButton} from "@web/views/view_button/view_button";
import {patch} from "@web/core/utils/patch";

patch(ViewButton, "Add hotkey to button", {
    props: [...ViewButton.props, "hotkey?"],
});
