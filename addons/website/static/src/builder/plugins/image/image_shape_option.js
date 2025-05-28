import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { toRatio } from "@html_builder/utils/utils";
import { ShapeSelector } from "../shape/shape_selector";

export class ImageShapeOption extends BaseOptionComponent {
    static template = "website.ImageShapeOption";
    static props = {};
    setup() {
        super.setup();
        this.customizeTabPlugin = this.env.editor.shared.customizeTab;
        this.imageShapeOption = this.env.editor.shared.imageShapeOption;
        this.toRatio = toRatio;
        this.state = useDomState((editingElement) => {
            let shape = editingElement.dataset.shape;
            if (shape) {
                shape = shape.replace("web_editor", "html_builder");
            }
            return {
                hasShape: !!shape,
                shapeLabel: this.imageShapeOption.getShapeLabel(shape),
                showImageShape0: this.isShapeVisible(editingElement, 0),
                showImageShape1: this.isShapeVisible(editingElement, 1),
                showImageShape2: this.isShapeVisible(editingElement, 2),
                showImageShape3: this.isShapeVisible(editingElement, 3),
                showImageShape4: this.isShapeVisible(editingElement, 4),
                showImageShapeTransform: this.imageShapeOption.isTransformableShape(shape),
                showImageShapeAnimation: this.imageShapeOption.isAnimableShape(shape),
                togglableRatio: this.imageShapeOption.isTogglableRatioShape(shape),
            };
        });
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
