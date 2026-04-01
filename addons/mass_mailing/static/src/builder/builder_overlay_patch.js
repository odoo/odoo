import { sizingGrid, sizingX, sizingY } from "@html_builder/core/builder_overlay/builder_overlay";
import { patch } from "@web/core/utils/patch";

patch(sizingX, {
    selector: sizingX.selector + ", .row > div",
    exclude: sizingX.exclude + ", .o_mail_no_options, .s_col_no_resize.row > div, .s_col_no_resize",
});
patch(sizingY, {
    selector: sizingY.selector + ", .o_mail_snippet_general, .o_mail_snippet_general .row > div",
    exclude: sizingY.exclude + ", .o_mail_no_options, .s_col_no_resize.row > div, .s_col_no_resize",
});
patch(sizingGrid, {
    exclude: sizingY.exclude + ", .o_mail_no_options, .s_col_no_resize.row > div, .s_col_no_resize",
});
