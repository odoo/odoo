import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { useDomState } from "@html_builder/core/utils";
import { ShapeSelector } from "@html_builder/plugins/shape/shape_selector";
import { deepCopy } from "@web/core/utils/objects";
import { loadImageInfo } from "@html_editor/utils/image_processing";
import { isImageSupportedForProcessing } from "@html_editor/main/media/image_post_process_plugin";
import { getMimetypeBeforeShape } from "@html_builder/utils/image";
import { ratioValueConverter } from "@html_builder/utils/utils";

export class ImageShapeOption extends BaseOptionComponent {
    static template = "html_builder.ImageShapeOption";
    static dependencies = ["customizeTab", "imageShapeOption"];
    static props = {
        withAnimatedShapes: { type: Boolean, optional: true },
    };
    static defaultProps = {
        withAnimatedShapes: true,
    };
    static components = { ShapeSelector };
    setup() {
        super.setup();
        this.customizeTabPlugin = this.dependencies.customizeTab;
        this.imageShapeOption = this.dependencies.imageShapeOption;
        this.ratioValueConverter = ratioValueConverter();
        this.state = useDomState(async (editingElement) => {
            const { originalSrc } = editingElement.dataset.originalSrc
                ? editingElement.dataset
                : await loadImageInfo(editingElement);
            const shape = editingElement.dataset.shape;
            const imageShapeColorNames = [0, 1, 2, 3, 4].map((i) =>
                this.isShapeVisible(editingElement, i)
            );
            const mimetype = await getMimetypeBeforeShape(editingElement);
            const isImgSupportedForProcessing = await isImageSupportedForProcessing(
                editingElement,
                mimetype
            );
            return {
                hasShape: !!shape && !this.imageShapeOption.isTechnicalShape(shape),
                shapeLabel: this.imageShapeOption.getShapeLabel(shape),
                imageShapeColorNames: imageShapeColorNames,
                showImageShapeTransform: this.imageShapeOption.isTransformableShape(shape),
                showImageShapeAnimation: this.imageShapeOption.isAnimableShape(shape),
                togglableRatio:
                    this.imageShapeOption.isTogglableRatioShape(shape) &&
                    isImgSupportedForProcessing,
                hasShapeTransformation:
                    !!editingElement.dataset.shapeFlip ||
                    !!parseInt(editingElement.dataset.shapeRotate),
                isShapeSupported: !!originalSrc,
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
