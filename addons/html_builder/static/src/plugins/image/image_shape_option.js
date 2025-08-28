import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { toRatio } from "@html_builder/utils/utils";
import { ShapeSelector } from "@html_builder/plugins/shape/shape_selector";
import { deepCopy } from "@web/core/utils/objects";

export class ImageShapeOption extends BaseOptionComponent {
    static template = "html_builder.ImageShapeOption";
    static props = {
        withAnimatedShapes: { type: Boolean, optional: true },
        getFilteredGroups: Function,
    };
    static defaultProps = {
        withAnimatedShapes: true,
    };
    static components = { ShapeSelector };
    setup() {
        super.setup();
        this.props.getFilteredGroups = this.getFilteredGroups.bind(this);
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
    getFilteredGroups() {
        if (this.props.withAnimatedShapes) {
            return this.imageShapeOption.getImageShapeGroups();
        }
        const allDefinitions = deepCopy(this.imageShapeOption.getImageShapeGroups());
        for (const [dName, definition] of Object.entries(allDefinitions)) {
            for (const [gName, subgroup] of Object.entries(definition.subgroups)) {
                for (const [sName, shape] of Object.entries(subgroup.shapes)) {
                    if (shape.animated) {
                        delete subgroup.shapes[sName];
                    }
                }
                if (Object.keys(subgroup.shapes).length === 0) {
                    delete definition.subgroups[gName];
                }
            }
            if (Object.keys(definition.subgroups).length === 0) {
                delete allDefinitions[dName];
            }
        }
        return allDefinitions;
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
}
