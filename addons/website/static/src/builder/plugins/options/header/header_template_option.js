import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { useProps, t } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { convertCSSColorToRgba } from "@web/core/utils/colors";
import { useDomState } from "@html_builder/core/utils";
import { getCSSVariableValue } from "@html_editor/utils/formatting";

export class HeaderTemplateOption extends BaseOptionComponent {
    static id = "header_template_option";
    static template = "website.HeaderTemplateOption";
    static dependencies = ["headerOption"];

    setup() {
        super.setup();
        this.headerTemplates = this.dependencies.headerOption.getHeaderTemplates();
        this.domState = useDomState((editingElement) => ({
            isBlurAvailable: isHeaderBgBlurAvailable(editingElement),
        }));
    }

    hasSomeOptions(opts) {
        return opts.some((opt) => this.isActiveItem(opt));
    }
}

registry.category("website-options").add(HeaderTemplateOption.id, HeaderTemplateOption);

export class HeaderTemplateChoice extends BaseOptionComponent {
    static template = "website.HeaderTemplateChoice";
    props = useProps({
        title: t.string(),
        views: t.array(),
        varName: t.string(),
        imgSrc: t.string(),
        id: t.string(),
        menuShadowClass: t.string(),
        defaultAlignment: t.object().optional(),
    });
}

/**
 * Checks whether the header background blur is available.
 *
 * A background blur is only visible when the header background is at least
 * partially transparent.
 *
 * @param {HTMLElement} editingElement
 * @returns {boolean}
 */
export function isHeaderBgBlurAvailable(editingElement) {
    const headerNavEl = editingElement.querySelector("nav");
    if (!headerNavEl) {
        return;
    }
    const navStyle = getComputedStyle(headerNavEl);
    // The background color can come from the "theme" color, so if no custom or
    // gradient color is defined, we should check it to determine transparency.
    // We can't just use the header's "backgroundColor" or "backgroundImage",
    // because if the header is set to "Over the content", it's rendered
    // transparent when it's not scrolled, which can cause false positives.
    const menuColorCombination = parseInt(getCSSVariableValue("menu", navStyle));
    const getMenuColor = (color) =>
        Number.isInteger(menuColorCombination) &&
        getCSSVariableValue(`o-cc${menuColorCombination}-${color}`, navStyle);

    const bgColor = getCSSVariableValue("menu-custom", navStyle) || getMenuColor("bg");
    let bgGradient = getCSSVariableValue("menu-gradient", navStyle) || getMenuColor("bg-gradient");
    bgGradient = bgGradient === "none" ? "" : bgGradient;

    // Should be available if no color is defined (fully transparent).
    if (!bgColor && !bgGradient) {
        return true;
    }

    if (bgColor && convertCSSColorToRgba(bgColor).opacity < 100 && !bgGradient) {
        return true;
    }
    const hasRgbaOpacity = !!bgGradient && /rgba/i.test(bgGradient);

    // Check if there is at least one hex color with opacity.
    const hasHexOpacity =
        !!bgGradient &&
        !!bgGradient.match(/#[0-9a-f]{8}/gi)?.some((hex) => hex.slice(-2).toLowerCase() !== "ff");
    return hasRgbaOpacity || hasHexOpacity;
}
