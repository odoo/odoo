import { BaseOptionComponent } from "@html_builder/core/utils";
import { getBgImageURLFromEl, normalizeColor } from "@html_builder/utils/utils_css";
import { ImageSize } from "../image/image_size";
import { getHtmlStyle } from "@html_editor/utils/formatting";

export class BackgroundImageOption extends BaseOptionComponent {
    static template = "html_builder.BackgroundImageOption";
    static dependencies = ["history", "backgroundImageOption"];
    static components = { ImageSize };
    setup() {
        this.editingElement = this.env.getEditingElement();
        super.setup();
        // done here because we have direct access to the editing element
        // (which we don't have in the normalize of the current plugin)
        this.toggleBgImageClasses();
    }
    toggleBgImageClasses() {
        this.dependencies.history.ignoreDOMMutations(() => {
            const backgroundURL = getBgImageURLFromEl(this.editingElement);
            this.dependencies.backgroundImageOption.setImageBackground(this.editingElement, backgroundURL);
        });
    }
    showMainColorPicker() {
        const src = new URL(getBgImageURLFromEl(this.editingElement), window.location.origin);
        return (
            src.origin === window.location.origin &&
            (src.pathname.startsWith("/html_editor/shape/") ||
                src.pathname.startsWith("/web_editor/shape/"))
        );
    }
    getColorPickerColorNames() {
        const colorNames = [];
        for (let nbr = 1; nbr <= 5; nbr++) {
            const colorName = `c${nbr}`;
            if (getBackgroundImageColor(this.editingElement, colorName)) {
                colorNames.push(colorName);
            }
        }
        return colorNames;
    }
}

export function getBackgroundImageColor(editingEl, colorName) {
    const backgroundImageColor = new URL(
        getBgImageURLFromEl(editingEl),
        window.location.origin
    ).searchParams.get(colorName);
    if (backgroundImageColor) {
        return normalizeColor(backgroundImageColor, getHtmlStyle(editingEl.ownerDocument));
    }
}
