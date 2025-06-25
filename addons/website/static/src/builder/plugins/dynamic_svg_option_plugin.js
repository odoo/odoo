import { registry } from "@web/core/registry";
import { Plugin } from "@html_editor/plugin";
import { DynamicSvgOption } from "./dynamic_svg_option";
import { normalizeCSSColor } from "@web/core/utils/colors";
import { loadImage } from "@html_editor/utils/image_processing";
import { withSequence } from "@html_editor/utils/resource";
import { DYNAMIC_SVG } from "@html_builder/utils/option_sequence";
import { BuilderAction } from "@html_builder/core/builder_action";

class DynamicSvgOptionPlugin extends Plugin {
    static id = "DynamicSvgOption";
    resources = {
        builder_options: [
            withSequence(DYNAMIC_SVG, {
                OptionComponent: DynamicSvgOption,
                props: {},
                selector: "img[src^='/html_editor/shape/'], img[src^='/web_editor/shape/']",
            }),
        ],
        builder_actions: {
            SvgColorAction,
        },
    };
}

export class SvgColorAction extends BuilderAction {
    static id = "svgColor";
    getValue({ editingElement: imgEl, params: { mainParam: colorName } }) {
        const searchParams = new URL(imgEl.src, window.location.origin).searchParams;
        return searchParams.get(colorName);
    }
    async load({ editingElement: imgEl, params: { mainParam: colorName }, value: color }) {
        const newURL = new URL(imgEl.src, window.location.origin);
        newURL.searchParams.set(colorName, normalizeCSSColor(color));
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
