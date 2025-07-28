import { registry } from "@web/core/registry";
import { Plugin } from "@html_editor/plugin";
import { DynamicSvgOption } from "./dynamic_svg_option";
import { normalizeCSSColor } from "@web/core/utils/colors";
import { getCSSVariableValue, getHtmlStyle } from "@html_editor/utils/formatting";
import { loadImage } from "@html_editor/utils/image_processing";
import { withSequence } from "@html_editor/utils/resource";
import { DYNAMIC_SVG } from "@html_builder/utils/option_sequence";
import { BuilderAction } from "@html_builder/core/builder_action";

class DynamicSvgOptionPlugin extends Plugin {
    static id = "DynamicSvgOption";
    resources = {
        builder_options: [withSequence(DYNAMIC_SVG, DynamicSvgOption)],
        builder_actions: {
            SvgColorAction,
        },
    };
}

export class SvgColorAction extends BuilderAction {
    static id = "svgColor";
    getValue({ editingElement: imgEl, params: { mainParam: colorName } }) {
        const searchParams = new URL(imgEl.src, window.location.origin).searchParams;
        const color = searchParams.get(colorName);
        return /^o-color-[1-5]$/.test(color)
            ? getCSSVariableValue(color, getHtmlStyle(this.document))
            : normalizeCSSColor(color);
    }
    colorToSearchParams(color) {
        const cssVarMatch = color.match(/var\(--(.+)\)/);
        if (cssVarMatch === null) {
            return normalizeCSSColor(color);
        }
        // If it is a palette color, return the variable name
        if (/^o-color-[1-5]$/.test(cssVarMatch[1])) {
            return cssVarMatch[1];
        }
        // If it is a CSS variable, extract the color value
        return getCSSVariableValue(cssVarMatch[1], getHtmlStyle(this.document));
    }
    async load({ editingElement: imgEl, params: { mainParam: colorName }, value: color }) {
        const newURL = new URL(imgEl.src, window.location.origin);
        newURL.searchParams.set(colorName, this.colorToSearchParams(color));
        const src = newURL.pathname + newURL.search;
        await loadImage(src);
        return src;
    }
    apply({
        editingElement: imgEl,
        params: { mainParam: colorName },
        value: color,
        loadResult: newSrc,
    }) {
        imgEl.setAttribute("src", newSrc);
    }
}

registry.category("website-plugins").add(DynamicSvgOptionPlugin.id, DynamicSvgOptionPlugin);
