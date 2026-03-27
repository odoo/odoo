import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { toRatio } from "@html_builder/utils/utils";
import { getBgImageURLFromEl } from "@html_builder/utils/utils_css";
import { _t } from "@web/core/l10n/translation";

export class BackgroundShapeOption extends BaseOptionComponent {
    static template = "html_builder.BackgroundShapeOption";
    static dependencies = ["backgroundShapeOption"];
    setup() {
        super.setup();
        this.backgroundShapePlugin = this.dependencies.backgroundShapeOption;
        this.toRatio = toRatio;
        this.state = useDomState((editingElement) => {
            const shapeData = this.backgroundShapePlugin.getShapeData(editingElement);
            const shapeInfo = this.backgroundShapePlugin.getBackgroundShapes()[shapeData.shape];
            return {
                shapeName: shapeInfo?.selectLabel || _t("None"),
                isAnimated: shapeInfo?.animated,
            };
        });
    }
    showBackgroundShapes() {
        this.backgroundShapePlugin.showBackgroundShapes(this.env.getEditingElements());
    }
    getDefaultColorNames() {
        const editingEl = this.env.getEditingElement();
        return Object.keys(getDefaultColors(editingEl));
    }
}

/**
 * Returns the default colors for the currently selected shape.
 *
 * @param {HTMLElement} editingElement the element on which to read the
 * shape data.
 */
export function getDefaultColors(editingElement) {
    const shapeContainerEl = editingElement.querySelector(":scope > .o_we_shape");
    if (!shapeContainerEl) {
        return {};
    }
    const shapeContainerClonedEl = shapeContainerEl.cloneNode(true);
    shapeContainerClonedEl.classList.add("d-none");
    // Needs to be in document for bg-image class to take effect
    editingElement.ownerDocument.body.appendChild(shapeContainerClonedEl);
    shapeContainerClonedEl.style.setProperty("background-image", "");
    const shapeSrc = shapeContainerClonedEl && getBgImageURLFromEl(shapeContainerClonedEl);
    shapeContainerClonedEl.remove();
    if (!shapeSrc) {
        return {};
    }
    const url = new URL(shapeSrc, window.location.origin);
    return Object.fromEntries(url.searchParams.entries());
}
