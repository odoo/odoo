import { registry } from "@web/core/registry";
import { Plugin } from "@html_editor/plugin";
import { DynamicSvgOption } from "./dynamic_svg_option";
import { normalizeCSSColor } from "@web/core/utils/colors";
import { loadImage } from "@html_editor/utils/image_processing";

class DynamicSvgOptionPlugin extends Plugin {
    static id = "DynamicSvgOption";
    resources = {
        builder_options: [
            {
                OptionComponent: DynamicSvgOption,
                props: {},
                selector: "img[src^='/html_editor/shape/'], img[src^='/web_editor/shape/']",
            },
        ],
        builder_actions: this.getActions(),
    };

    getActions() {
        return {
            svgColor: {
                getValue: ({ editingElement: imgEl, param: { mainParam: colorName } }) => {
                    const searchParams = new URL(imgEl.src, window.location.origin).searchParams;
                    return searchParams.get(colorName);
                },
                load: async ({
                    editingElement: imgEl,
                    param: { mainParam: colorName },
                    value: color,
                }) => {
                    const newURL = new URL(imgEl.src, window.location.origin);
                    newURL.searchParams.set(colorName, normalizeCSSColor(color));
                    const src = newURL.pathname + newURL.search;
                    await loadImage(src);
                    return src;
                },
                apply: ({
                    editingElement: imgEl,
                    param: { mainParam: colorName },
                    value: color,
                    loadResult: newSrc,
                }) => {
                    imgEl.setAttribute("src", newSrc);
                },
            },
        };
    }
}

registry.category("website-plugins").add(DynamicSvgOptionPlugin.id, DynamicSvgOptionPlugin);
