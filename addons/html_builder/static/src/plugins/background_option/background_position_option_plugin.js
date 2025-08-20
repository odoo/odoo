import { getBgImageURLFromEl } from "@html_builder/utils/utils_css";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { BackgroundPositionOverlay } from "./background_position_overlay";
import { BuilderAction } from "@html_builder/core/builder_action";
import { loadImage } from "@html_editor/utils/image_processing";

const getBgSizeValue = function ({ editingElement, params: { mainParam: styleName } }) {
    const backgroundSize = editingElement.style.backgroundSize;
    const bgWidthAndHeight = backgroundSize.split(/\s+/g);
    const value = styleName === "width" ? bgWidthAndHeight[0] : bgWidthAndHeight[1] || "";
    return value === "auto" ? "" : value;
};

class BackgroundPositionOptionPlugin extends Plugin {
    static id = "backgroundPositionOption";
    static dependencies = ["overlay", "overlayButtons"];
    resources = {
        builder_actions: {
            BackgroundTypeAction,
            SetBackgroundSizeAction,
            BackgroundPositionOverlayAction,
        },
    };
}

export class BackgroundTypeAction extends BuilderAction {
    static id = "backgroundType";
    apply({ editingElement, value }) {
        editingElement.classList.toggle("o_bg_img_opt_repeat", value === "repeat-pattern");
        editingElement.style.setProperty("background-position", "");
        editingElement.style.setProperty(
            "background-size",
            value !== "repeat-pattern" ? "" : "100px"
        );
    }
    isApplied({ editingElement, value }) {
        const hasElRepeatStyle = getComputedStyle(editingElement).backgroundRepeat === "repeat";
        return value === "repeat-pattern" ? hasElRepeatStyle : !hasElRepeatStyle;
    }
}

export class SetBackgroundSizeAction extends BuilderAction {
    static id = "setBackgroundSize";
    getValue(context) {
        return getBgSizeValue(context);
    }
    apply({ editingElement, params: { mainParam: styleName }, value }) {
        const otherParam = styleName === "width" ? "height" : "width";
        let otherBgSize = getBgSizeValue({
            editingElement: editingElement,
            params: { mainParam: otherParam },
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
    }
}

export class BackgroundPositionOverlayAction extends BuilderAction {
    static id = "backgroundPositionOverlay";
    static dependencies = ["overlayButtons", "history"];
    setup() {
        this.withLoadingEffect = false;
    }
    async load({ editingElement }) {
        const imgEl = await loadImage(getBgImageURLFromEl(editingElement));
        return new Promise((resolve) => {
            // Hide the builder overlay buttons when the user changes
            // the background position.
            this.dependencies.overlayButtons.hideOverlayButtonsUi();
            let appliedBgPosition = "";
            const onRemove = () => {
                this.dependencies.overlayButtons.showOverlayButtonsUi();
                resolve(appliedBgPosition);
            };
            const removeOverlay = this.services.overlay.add(
                BackgroundPositionOverlay,
                {
                    editingElement: editingElement,
                    mockEditingElOnImg: imgEl,
                    applyPosition: (bgPosition) => {
                        appliedBgPosition = bgPosition;
                        removeOverlay();
                    },
                    discardPosition: () => removeOverlay(),
                    editable: this.editable,
                    history: {
                        makeSavePoint: this.dependencies.history.makeSavePoint,
                    },
                },
                { onRemove }
            );
        });
    }
    apply({ editingElement, loadResult: bgPosition }) {
        if (bgPosition) {
            editingElement.style.backgroundPosition = bgPosition;
        }
    }
}

registry
    .category("builder-plugins")
    .add(BackgroundPositionOptionPlugin.id, BackgroundPositionOptionPlugin);
