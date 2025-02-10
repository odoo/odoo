import { useIsActiveItem } from "@html_builder/core/building_blocks/utils";
import { defaultBuilderComponents } from "@html_builder/core/default_builder_components";
import { Plugin } from "@html_editor/plugin";
import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";

const getBgSizeValue = function ({ editingElement, param: styleName }) {
    const backgroundSize = editingElement.style.backgroundSize;
    const bgWidthAndHeight = backgroundSize.split(/\s+/g);
    const value = styleName === "width" ? bgWidthAndHeight[0] : bgWidthAndHeight[1] || "";
    return value === "auto" ? "" : value;
};

class BackgroundPositionPlugin extends Plugin {
    static id = "BackgroundPosition";
    resources = {
        builder_actions: this.getActions(),
    };
    getActions() {
        return {
            backgroundType: {
                apply: ({ editingElement, value }) => {
                    editingElement.classList.toggle(
                        "o_bg_img_opt_repeat",
                        value === "repeat-pattern"
                    );
                    editingElement.style.setProperty("background-position", "");
                    editingElement.style.setProperty(
                        "background-size",
                        value !== "repeat-pattern" ? "" : "100px"
                    );
                },
                isApplied: ({ editingElement, value }) => {
                    const hasElRepeatStyle =
                        getComputedStyle(editingElement).backgroundRepeat === "repeat";
                    return value === "repeat-pattern" ? hasElRepeatStyle : !hasElRepeatStyle;
                },
            },
            setBackgroundSize: {
                getValue: getBgSizeValue,
                apply: ({ editingElement, param: styleName, value }) => {
                    const otherParam = styleName === "width" ? "height" : "width";
                    let otherBgSize = getBgSizeValue({
                        editingElement: editingElement,
                        param: otherParam,
                    });
                    let bgSize;
                    if (styleName === "width") {
                        value = !value && otherBgSize ? "auto" : value;
                        otherBgSize = otherBgSize === "" ? "" : ` ${otherBgSize}`;
                        bgSize = `${value}${otherBgSize}`;
                    } else {
                        otherBgSize ||= "auto";
                        bgSize = `${otherBgSize} ${value}`;
                    }
                    editingElement.style.setProperty("background-size", bgSize);
                },
            },
        };
    }
}

registry.category("website-plugins").add(BackgroundPositionPlugin.id, BackgroundPositionPlugin);

export class BackgroundPosition extends Component {
    static template = "html_builder.BackgroundPosition";
    static components = {
        ...defaultBuilderComponents,
    };
    static props = {};
    setup() {
        this.isActiveItem = useIsActiveItem();
    }
}
