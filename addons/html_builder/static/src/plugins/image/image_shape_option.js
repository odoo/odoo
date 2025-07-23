import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { toRatio } from "@html_builder/utils/utils";
import { _t } from "@web/core/l10n/translation";
import { ShapeSelector } from "@html_builder/plugins/shape/shape_selector";
import { deepCopy } from "@web/core/utils/objects";
import { BorderConfigurator } from "../border_configurator_option";
import { ShadowOption } from "../shadow_option";

export class ImageShapeOption extends BaseOptionComponent {
    static template = "html_builder.ImageShapeOption";
    static props = {
        withAnimatedShapes: { type: Boolean, optional: true },
    };
    static components = { BorderConfigurator, ShadowOption };
    static defaultProps = {
        withAnimatedShapes: true,
    };
    setup() {
        super.setup();
        this.customizeTabPlugin = this.env.editor.shared.customizeTab;
        this.imageShapeOption = this.env.editor.shared.imageShapeOption;
        this.toRatio = toRatio;
        this.shapeGroups = this.imageShapeOption.getImageShapeGroups();
        this.imageShapes = this.imageShapeOption.makeImageShapes();
        this.lastShape = "";

        this.state = useDomState((editingElement) => {
            let shape = editingElement.dataset.shape;

            if (this.lastShape != shape) {
                if (shape) {
                    shape = shape.replace("web_editor", "html_builder");
                    const shapeDef = this.imageShapes[shape] || null;
                    // Compatibility: older elements may only have `data-shape`.
                    // If its definition provides `imageShapeClass`, we sync it
                    // by setting the dataset and adding the classes.
                    if (shapeDef?.imageShapeClass) {
                        editingElement.dataset.imageShapeClass = shapeDef.imageShapeClass;
                        editingElement.classList.add(
                            ...shapeDef.imageShapeClass.trim().split(/\s+/)
                        );
                    }
                } else {
                    // If the `data-shape` is missing on the editing element,
                    // detect it by checking whether the element’s classes match
                    // any known `imageShapeClass`
                    shape = this.applyDetectedShape(editingElement);
                }
                this.lastShape = shape;
            }
            return {
                hasImageShapeClass: !!editingElement.dataset.imageShapeClass,
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
    /**
     * Select the shape of an element based on its applied CSS classes.
     *
     * This function compares the element’s class list against all known
     * shapes that define an `imageShapeClass`. If a match is found, the
     * element’s dataset is updated with the detected `shapeKey` and
     * `imageShapeClass`.
     *
     * Shapes with more required classes (e.g. "a b") are prioritized over
     * simpler ones (e.g. "a") by sorting candidates by class count in
     * descending order.
     *
     * Example:
     *   - shape 1 -> imageShapeClass: "a"
     *   - shape 2 -> imageShapeClass: "a b"
     *
     *   If the element has only class "a":
     *     - shape 1 will be selected.
     *   If the element has classes "a b":
     *     - shape 2 will be selected (more specific match).
     *
     * @param {HTMLElement} el editing element
     * @returns {string|null} The detected shape key, or null if none
     *                        match
     */
    applyDetectedShape(el) {
        const candidates = [];

        for (const [shapeKey, shapeDef] of Object.entries(this.imageShapes)) {
            if (!shapeDef.imageShapeClass) {
                continue;
            }
            const matchingClasses = shapeDef.imageShapeClass.trim().split(/\s+/);
            candidates.push({
                shapeKey,
                imageShapeClass: shapeDef.imageShapeClass,
                matchingClasses,
            });
        }

        // Sort candidates so that shapes with more required classes are matched
        // first
        candidates.sort((a, b) => b.matchingClasses.length - a.matchingClasses.length);

        for (const { shapeKey, imageShapeClass, matchingClasses } of candidates) {
            if (matchingClasses.every((c) => el.classList.contains(c))) {
                el.dataset.shape = shapeKey;
                el.dataset.imageShapeClass = imageShapeClass;
                return shapeKey;
            }
        }
        return null;
    }
    getFilteredGroups() {
        if (this.props.withAnimatedShapes) {
            return this.shapeGroups;
        }
        const allDefinitions = deepCopy(this.shapeGroups);
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
    showImageShapes() {
        this.customizeTabPlugin.openCustomizeComponent(
            ShapeSelector,
            this.env.getEditingElements(),
            {
                shapeActionId: "setImageShape",
                buttonWrapperClassName: "o-hb-img-shape-btn",
                selectorTitle: _t("Shapes"),
                shapeGroups: this.getFilteredGroups(),
            }
        );
    }
}
