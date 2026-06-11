import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { registry } from "@web/core/registry";
import { convertCSSColorToRgba } from "@web/core/utils/colors";
import { getCSSVariableValue, getHtmlStyle } from "@html_editor/utils/formatting";
import { useDomState } from "@html_builder/core/utils";

export class HeaderBgBlurOption extends BaseOptionComponent {
    static template = "website.HeaderBgBlurOption";

    static props = {
        ...BaseOptionComponent.props,
        level: { type: Number },
    };

    setup() {
        super.setup();
        this.blurState = useDomState(() => {
            const htmlStyle = getHtmlStyle(this.document);
            const blurValue = getCSSVariableValue("header-bg-blur", htmlStyle);
            return {
                show: isHeaderBgBlurAvailable(htmlStyle),
                hasBlur: parseFloat(blurValue) > 0,
            };
        });
    }
}

export class HeaderTemplateOption extends BaseOptionComponent {
    static id = "header_template_option";
    static template = "website.HeaderTemplateOption";
    static dependencies = ["headerOption"];
    static components = { HeaderBgBlurOption };

    setup() {
        super.setup();
        this.headerTemplates = this.dependencies.headerOption.getHeaderTemplates();
    }

    hasSomeOptions(opts) {
        return opts.some((opt) => this.isActiveItem(opt));
    }
}

registry.category("website-options").add(HeaderTemplateOption.id, HeaderTemplateOption);

export class HeaderTemplateChoice extends BaseOptionComponent {
    static template = "website.HeaderTemplateChoice";
    static props = {
        title: String,
        views: Array,
        varName: String,
        imgSrc: String,
        id: String,
        menuShadowClass: String,
        defaultAlignment: { type: Object, optional: true },
    };
}

/**
 * Checks whether the header background blur is available.
 *
 * A background blur is only visible when the header background is at least
 * partially transparent.
 *
 * @param {CSSStyleDeclaration} htmlStyle
 * @param {Object<string, string>} [styleOverrides]
 * @returns {boolean}
 */
export function isHeaderBgBlurAvailable(htmlStyle, styleOverrides = {}) {
    const bgColor =
        "menu-custom" in styleOverrides
            ? styleOverrides["menu-custom"]
            : getCSSVariableValue("menu-custom", htmlStyle);
    const bgColorOpacity = convertCSSColorToRgba(bgColor).opacity;
    if (bgColorOpacity >= 0 && bgColorOpacity < 100) {
        return true;
    }
    const bgGradient =
        "menu-gradient" in styleOverrides
            ? styleOverrides["menu-gradient"]
            : getCSSVariableValue("menu-gradient", htmlStyle);
    const hasRgbaOpacity = /rgba/i.test(bgGradient);

    // Check if there is at least one hex color with opacity.
    const hasHexOpacity = !!bgGradient
        .match(/#[0-9a-f]{8}/gi)
        ?.some((hex) => hex.slice(-2).toLowerCase() !== "ff");
    return hasRgbaOpacity || hasHexOpacity;
}
