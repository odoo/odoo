import { defaultBuilderComponents } from "@html_builder/core/default_builder_components";
import { Component } from "@odoo/owl";
import { ShapeSelector } from "../shape/shape_selector";
import { useDomState } from "@html_builder/core/building_blocks/utils";

export class ImageShapeOption extends Component {
    static template = "html_builder.ImageShapeOption";
    static components = { ...defaultBuilderComponents };
    static props = {};
    setup() {
        this.customizeTabPlugin = this.env.editor.shared.customizeTab;
        this.imageShapeOption = this.env.editor.shared.imageShapeOption;
        this.state = useDomState((editingElement) => ({
            hasShape: !!editingElement.dataset.shape,
            showImageShape0: this.isShapeVisible(editingElement, 0),
            showImageShape1: this.isShapeVisible(editingElement, 1),
            showImageShape2: this.isShapeVisible(editingElement, 2),
            showImageShape3: this.isShapeVisible(editingElement, 3),
            showImageShape4: this.isShapeVisible(editingElement, 4),
            showImageShapeTransform: true,
        }));
    }
    isShapeVisible(img, shapeIndex) {
        const shapeName = img.dataset.shape;
        const shapeColors = img.dataset.shapeColors;
        if (!shapeName || !shapeColors) {
            return false;
        }
        const colors = img.dataset.shapeColors.split(";");
        return colors[shapeIndex];
    }
    showImageShapes() {
        this.customizeTabPlugin.openCustomizeComponent(
            ShapeSelector,
            this.env.getEditingElements(),
            {
                shapeActionId: "setImageShape",
                shapeGroups: this.imageShapeOption.getImageShapeGroups(),
            }
        );
    }
}
