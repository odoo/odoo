import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";

export class ImageGridOption extends BaseOptionComponent {
    static template = "website.ImageGridOption";
    static props = {};

    setup() {
        super.setup();
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
