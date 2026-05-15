import { patch } from "@web/core/utils/patch";
import { MassMailingHtmlField } from "@mass_mailing/fields/html_field/mass_mailing_html_field";
import { useService } from "@web/core/utils/hooks";
import { DebugConvertInlineDialog } from "./debug_convert_inline_dialog";
import { parseHTML } from "@html_editor/utils/html";

patch(MassMailingHtmlField.prototype, {
    setup() {
        super.setup();
        this.dialog = useService("dialog");
    },
    async debugConvertInline() {
        const el = await this.getEditorContent();
        const content = el.innerHTML;
        this.dialog.add(DebugConvertInlineDialog, {
            fragment: parseHTML(document, content),
        });
    },
});
