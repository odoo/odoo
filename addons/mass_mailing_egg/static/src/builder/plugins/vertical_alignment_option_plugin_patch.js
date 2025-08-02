import { VerticalAlignmentOptionPlugin } from "@html_builder/plugins/vertical_alignment_option_plugin";
import { patch } from "@web/core/utils/patch";

patch(VerticalAlignmentOptionPlugin.prototype, {
    get selector() {
        return super.selector + ", .s_mail_block_event";
    }
})
