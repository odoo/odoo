import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { toRatio } from "@html_builder/utils/utils";
import { _t } from "@web/core/l10n/translation";
import { ShapeSelector } from "@html_builder/plugins/shape/shape_selector";

export class ImageShapeOption extends BaseOptionComponent {
    static template = "html_builder.ImageShapeOption";
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
                hasShape: !!shape && !this.imageShapeOption.isTechnicalShape(shape),
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
                buttonWrapperClassName: "o-hb-img-shape-btn",
                selectorTitle: _t("Shapes"),
                shapeGroups: this.imageShapeOption.getImageShapeGroups(),
            }
        );
    }
}
