import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import { BuilderAction } from "@html_builder/core/builder_action";

export class ProductAttributeOptionPlugin extends Plugin {
    static id = "productAttributeOption";
    resources = {
        builder_actions: {
            ProductAttributeDisplayAction,
            ProductAttributeThumbnailAction,
        },
    };

}

export class BaseProductAttributeAction extends BuilderAction {
    setup() {
        this.reload = {};
    }
    getAttributeEl(el) {
        return el.closest(".variant_attribute");
    }
    saveAttributeConfig(el, displayVals) {
        return rpc("/shop/config/attribute", {
            attribute_id: parseInt(this.getAttributeEl(el).dataset.attributeId),
            ...displayVals,
        });
    }
}

export class ProductAttributeDisplayAction extends BaseProductAttributeAction {
    static id = "productAttributeDisplay";

    isApplied({ editingElement: el, value }) {
        return value === this.getValue({ editingElement: el });
    }
    getValue({ editingElement: el }) {
        return this.getAttributeEl(el).dataset.attributeDisplayType;
    }
    apply({ editingElement: el, value }) {
        return this.saveAttributeConfig(el, { display_type: value });
    }
}

export class ProductAttributeThumbnailAction extends BaseProductAttributeAction {
    static id = "productAttributeThumbnail";

    isApplied({ editingElement: el }) {
        return !!this.getAttributeEl(el).dataset.attributeIsThumbnailVisible;
    }
    apply({ editingElement: el }) {
        return this.saveAttributeConfig(el, { is_thumbnail_visible: true });
    }
    clean({ editingElement: el }) {
        return this.saveAttributeConfig(el, { is_thumbnail_visible: false });
    }
}

registry
    .category("website-plugins")
    .add(ProductAttributeOptionPlugin.id, ProductAttributeOptionPlugin);
