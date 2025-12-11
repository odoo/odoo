import { ListRenderer } from "@web/views/list/list_renderer";
import { patch } from "@web/core/utils/patch";

patch(ListRenderer.prototype, {
    get widgetsToIgnore() {
        return ["product_label_section_and_note_field", ...super.widgetsToIgnore];
    }
});
