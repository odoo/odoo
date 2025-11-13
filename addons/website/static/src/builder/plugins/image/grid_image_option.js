import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";

export class GridImageOption extends BaseOptionComponent {
    static template = "website.GridImageOption";
    static selector = "img";

    setup() {
        super.setup();
        this.state = useDomState((editingElement) => ({
            isOptionActive: this.isOptionActive(editingElement),
        }));
    }

    isOptionActive(editingElement) {
        const imageGridItemEl = editingElement.closest(".o_grid_item_image");
        // Special conditions for the hover effects.
        const hasSquareShape = editingElement.dataset.shape === "html_builder/geometric/geo_square";
        const effectAllowsOption = !["dolly_zoom", "outline", "image_mirror_blur"].includes(
            editingElement.dataset.hoverEffect
        );

        return (
            !!imageGridItemEl &&
            (!("shape" in editingElement.dataset) || (hasSquareShape && effectAllowsOption))
        );
    }
}
