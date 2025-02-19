import { getBgImageURLFromEl } from "@html_builder/utils/utils_css";
import { Plugin } from "@html_editor/plugin";
import { markup } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { BackgroundPositionOverlay } from "./background_position_overlay";

const getBgSizeValue = function ({ editingElement, param: { mainParam: styleName } }) {
    const backgroundSize = editingElement.style.backgroundSize;
    const bgWidthAndHeight = backgroundSize.split(/\s+/g);
    const value = styleName === "width" ? bgWidthAndHeight[0] : bgWidthAndHeight[1] || "";
    return value === "auto" ? "" : value;
};

class BackgroundPositionOptionPlugin extends Plugin {
    static id = "backgroundPositionOption";
    static dependencies = ["overlay", "overlayButtons"];
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
                apply: ({ editingElement, param: { mainParam: styleName }, value }) => {
                    const otherParam = styleName === "width" ? "height" : "width";
                    let otherBgSize = getBgSizeValue({
                        editingElement: editingElement,
                        param: { mainParam: otherParam },
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
            backgroundPositionOverlay: {
                load: async ({ editingElement }) => {
                    let imgEl;
                    await new Promise((resolve) => {
                        imgEl = document.createElement("img");
                        imgEl.addEventListener("load", () => resolve());
                        imgEl.src = getBgImageURLFromEl(editingElement);
                    });
                    const copyEl = editingElement.cloneNode(false);
                    copyEl.classList.remove("o_editable");
                    // Hide the builder overlay buttons when the user changes
                    // the background position.
                    return new Promise((resolve) => {
                        this.dependencies.overlayButtons.hideOverlayButtonsUi();
                        let appliedBgPosition = "";
                        const onRemove = () => {
                            this.dependencies.overlayButtons.showOverlayButtonsUi();
                            resolve(appliedBgPosition);
                        };
                        const overlay = this.dependencies.overlay.createOverlay(
                            BackgroundPositionOverlay,
                            { positionOptions: { position: "over-fit", flip: false } },
                            { onRemove: onRemove }
                        );
                        const applyPosition = (bgPosition) => {
                            appliedBgPosition = bgPosition;
                            overlay.close();
                        };
                        overlay.open({
                            target: editingElement,
                            props: {
                                outerHtmlEditingElement: markup(copyEl.outerHTML),
                                editingElement: editingElement,
                                mockEditingElOnImg: imgEl,
                                applyPosition: applyPosition,
                                discardPosition: () => overlay.close(),
                                editable: this.editable,
                            },
                        });
                    });
                },
                apply: ({ editingElement, loadResult: bgPosition }) => {
                    if (bgPosition) {
                        editingElement.style.backgroundPosition = bgPosition;
                    }
                },
            },
        };
    }
}

registry
    .category("website-plugins")
    .add(BackgroundPositionOptionPlugin.id, BackgroundPositionOptionPlugin);
