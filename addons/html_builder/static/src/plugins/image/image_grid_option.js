import { Component } from "@odoo/owl";
import { defaultBuilderComponents } from "@html_builder/core/default_builder_components";
import { useDomState } from "@html_builder/core/building_blocks/utils";

export class ImageGridOption extends Component {
    static template = "html_builder.ImageGridOption";
    static components = { ...defaultBuilderComponents };
    static props = {};

    setup() {
        this.state = useDomState((editingElement) => {
            const imageGridItemEl = editingElement.closest(".o_grid_item_image");
            return {
                isOptionActive: this.isOptionActive(editingElement, imageGridItemEl),
            };
        });
    }

    isOptionActive(editingElement, imageGridItemEl) {
        // Special conditions for the hover effects.
        const hasSquareShape = editingElement.dataset.shape === "web_editor/geometric/geo_square";
        const effectAllowsOption = !["dolly_zoom", "outline", "image_mirror_blur"].includes(
            editingElement.dataset.hoverEffect
        );

        return (
            !!imageGridItemEl &&
            (!("shape" in editingElement.dataset) || (hasSquareShape && effectAllowsOption))
        );
    }
}
