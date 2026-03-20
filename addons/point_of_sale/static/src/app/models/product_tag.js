import { Base } from "./related_models";
import { markup } from "@odoo/owl";
import { registry } from "@web/core/registry";

export class ProductTag extends Base {
    static pythonModel = "product.tag";

    get posDescriptionMarkup() {
        return this.pos_description ? markup(this.pos_description) : "";
    }
}

registry.category("pos_available_models").add(ProductTag.pythonModel, ProductTag);
