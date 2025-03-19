import { Component } from "@odoo/owl";
import { ShapeSelector } from "../shape/shape_selector";
import { useBuilderComponents, useDomState } from "@html_builder/core/utils";
import { toRatio } from "@html_builder/utils/utils";

export class ImageShapeOption extends Component {
    static template = "html_builder.ImageShapeOption";
    static props = {};
    setup() {
        useBuilderComponents();
        this.customizeTabPlugin = this.env.editor.shared.customizeTab;
        this.imageShapeOption = this.env.editor.shared.imageShapeOption;
        this.toRatio = toRatio;
        this.state = useDomState((editingElement) => ({
            hasShape: !!editingElement.dataset.shape,
            showImageShape0: this.isShapeVisible(editingElement, 0),
            showImageShape1: this.isShapeVisible(editingElement, 1),
            showImageShape2: this.isShapeVisible(editingElement, 2),
            showImageShape3: this.isShapeVisible(editingElement, 3),
            showImageShape4: this.isShapeVisible(editingElement, 4),
            showImageShapeTransform: this.imageShapeOption.isTransformableShape(
                editingElement.dataset.shape
            ),
            showImageShapeAnimation: this.imageShapeOption.isAnimableShape(
                editingElement.dataset.shape
            ),
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
