import { BaseOptionComponent } from "@html_builder/core/utils";
import { getBgImageURLFromEl, normalizeColor } from "@html_builder/utils/utils_css";
import { ImageSize } from "../image/image_size";
import { getHtmlStyle } from "@html_editor/utils/formatting";

export class BackgroundImageOption extends BaseOptionComponent {
    static template = "html_builder.BackgroundImageOption";
    static props = {};
    static components = { ImageSize };
    setup() {
        // done here because we have direct access to the editing element
        // (which we don't have in the normalize of the current plugin)
        this.toggleBgImageClasses();
        super.setup();
    }
    toggleBgImageClasses() {
        this.env.editor.shared.history.ignoreDOMMutations(() => {
            const editingEl = this.env.getEditingElement();
            const backgroundURL = getBgImageURLFromEl(editingEl);
            this.env.editor.shared.backgroundImageOption.setImageBackground(
                editingEl,
                backgroundURL
            );
        });
    }
    showMainColorPicker() {
        const editingEl = this.env.getEditingElement();
        const src = new URL(getBgImageURLFromEl(editingEl), window.location.origin);
        return (
            src.origin === window.location.origin &&
            (src.pathname.startsWith("/html_editor/shape/") ||
                src.pathname.startsWith("/web_editor/shape/"))
        );
    }
    getColorPickerColorNames() {
        const colorNames = [];
        const editingEl = this.env.getEditingElement();
        for (let nbr = 1; nbr <= 5; nbr++) {
            const colorName = `c${nbr}`;
            if (getBackgroundImageColor(editingEl, colorName)) {
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
