/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ViewButton } from "@web/views/view_button/view_button";
import { BUTTON_STRING_PROPS } from "@web/views/view_compiler";

BUTTON_STRING_PROPS.push("barcode_trigger");

patch(ViewButton, "view_button_barcode", {
    props: [...ViewButton.props, "barcode_trigger?"],
});
