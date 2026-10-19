import { registry } from "@web/core/registry";

import {
    X2ManyMediaViewer,
    x2ManyMediaViewer,
} from "@html_editor/fields/x2many_field/x2many_media_viewer";
import { ProductImageKanbanRenderer } from "./product_image_kanban_renderer";

export class ProductImageX2ManyMediaViewer extends X2ManyMediaViewer {
    static components = {
        ...X2ManyMediaViewer.components,
        KanbanRenderer: ProductImageKanbanRenderer,
    };
}

export const productImageX2ManyMediaViewer = {
    ...x2ManyMediaViewer,
    component: ProductImageX2ManyMediaViewer,
};

registry
    .category("fields")
    .add("product_image_x2_many_media_viewer", productImageX2ManyMediaViewer);
