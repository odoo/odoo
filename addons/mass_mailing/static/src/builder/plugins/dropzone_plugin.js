import { Plugin } from "@html_editor/plugin";
import { isPhrasingContent } from "@html_editor/utils/dom_info";
import { registry } from "@web/core/registry";

class DropzonePlugin extends Plugin {
    static id = "mass_mailing.DropzonePlugin";

    resources = {
        dropzone_selector: [
            {
                selector:
                    ".s_mail_blockquote, .s_mail_alert, .s_rating, .s_hr, .s_mail_text_highlight",
                dropNear:
                    "p, h1, h2, h3, ul, ol, .row > div > img, .s_mail_blockquote, .s_mail_alert, .s_rating, .s_hr, .s_mail_text_highlight",
                dropIn: ".content, nav",
            },
            {
                selector: "blockquote",
                dropNear: "section",
                dropIn: ".o_mail_wrapper_td",
            },
            {
                // table_column
                selector: ".col>td, .col>th",
                exclude: this.noOptionsSelector,
                dropNear: ".col>td, .col>th",
            },
            {
                // table_column_mv
                selector: ".col_mv, td, th",
                exclude: this.noOptionsSelector,
                dropNear: ".col_mv, td, th",
            },
            {
                // table_row
                selector: "tr:has(> .row), tr:has(> .col_mv)",
                exclude: this.noOptionsSelector,
                dropNear: "tr:has(> .row), tr:has(> .col_mv)",
            },
            {
                // content
                selector:
                    ".note-editable > div:not(.o_layout), .note-editable .oe_structure > *, .oe_snippet_body",
                exclude: this.noOptionsSelector,
                dropNear: "[data-oe-field='body_html']:not(:has(.o_layout)) > *, .oe_structure > *",
                dropIn: "[data-oe-field='body_html']:not(:has(.o_layout)), .oe_structure",
            },
            {
                // sizing_x
                selector: ".row > div",
                exclude: ".o_mail_no_options, .s_col_no_resize.row > div, .s_col_no_resize",
                dropNear: ".row:not(.s_col_no_resize) > div",
            },
        ],
        // Prevent dropping as phrasingContent siblings (reduces the amount of drop zones for
        // HR block).
        filter_for_sibling_dropzone_predicates: (el) => isPhrasingContent(el),
    };

    get noOptionsSelector() {
        return ".o_mail_no_options";
    }
}

registry.category("mass_mailing-plugins").add(DropzonePlugin.id, DropzonePlugin);
