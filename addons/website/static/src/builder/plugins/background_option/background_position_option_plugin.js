import { getBgImageURLFromEl } from "@html_builder/utils/utils_css";
import { Plugin } from "@html_editor/plugin";
import { markup } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { BackgroundPositionOverlay } from "./background_position_overlay";
import { BuilderAction } from "@html_builder/core/builder_action";

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
    static dependencies = ["overlayButtons", "overlay", "edit_interaction"];
    async load({ editingElement }) {
        const editInteraction = this.dependencies.edit_interaction;
        const parallaxEl = editingElement.closest(".parallax");
        if (parallaxEl) {
            editInteraction.stopInteractions(editingElement.closest(".parallax"));
        }
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
                if (parallaxEl) {
                    editInteraction.restartInteractions(editingElement.closest(".parallax"));
                }
            };
            const discardPosition = () => {
                overlay.close();
                if (parallaxEl) {
                    editInteraction.restartInteractions(editingElement.closest(".parallax"));
                }
            };
            overlay.open({
                target: editingElement,
                props: {
                    outerHtmlEditingElement: markup(this.safeCloneOuterHTML(copyEl)),
                    editable: this.editable,
                    mockEditingElOnImg: imgEl,
                    applyPosition,
                    discardPosition,
                    editingElement,
                },
            });
        });
    }
    safeCloneOuterHTML(el) {
        const copyEl = document.createElement(el.tagName);
        copyEl.style.cssText = el.style.cssText;
        copyEl.className = el.className;
        return copyEl.outerHTML;
    }
    apply({ editingElement, loadResult: bgPosition }) {
        if (bgPosition) {
            editingElement.style.backgroundPosition = bgPosition;
        }
    }
}

registry
    .category("website-plugins")
    .add(BackgroundPositionOptionPlugin.id, BackgroundPositionOptionPlugin);
