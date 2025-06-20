import {
    ProductLabelSectionAndNoteListRender,
    productLabelSectionAndNoteOne2Many,
    ProductLabelSectionAndNoteOne2Many,
} from '@account/components/product_label_section_and_note_field/product_label_section_and_note_field_o2m';
import { registry } from '@web/core/registry';

export class PurchaseOrderLineListRenderer extends ProductLabelSectionAndNoteListRender {
    static rowsTemplate = "web.ListRenderer.Rows";
    setup() {
        super.setup();
        this.sectionCols = [];
    }
}

export class PurchaseProductLabelSectionAndNoteOne2Many extends ProductLabelSectionAndNoteOne2Many {
    static components = {
        ...ProductLabelSectionAndNoteOne2Many.components,
        ListRenderer: PurchaseOrderLineListRenderer,
    };
}

export const purchaseProductLabelSectionAndNoteOne2Many = {
    ...productLabelSectionAndNoteOne2Many,
    component: PurchaseProductLabelSectionAndNoteOne2Many,
};

registry
    .category("fields")
    .add("purchase_product_label_section_and_note_field_o2m", purchaseProductLabelSectionAndNoteOne2Many);
