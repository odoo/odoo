import { getBgImageURLFromEl } from "@html_builder/utils/utils_css";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { ImagePositionOverlay } from "@html_builder/plugins/image/image_position_overlay";
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
    static shared = ["getDelta"];
    /** @type {import("plugins").BuilderResources} */
    resources = {
        builder_actions: {
            BackgroundTypeAction,
            SetBackgroundSizeAction,
            BackgroundPositionOverlayAction,
        },
    };

    getDelta(editingElement, imageEl) {
        const naturalWidth = imageEl.naturalWidth;
        const naturalHeight = imageEl.naturalHeight;
        const editingElStyle = getComputedStyle(editingElement);
        const iframeEl = this.editable.ownerDocument.defaultView.frameElement;

        // If background-attachment: fixed, the background is sized relative to
        // the page viewport.
        const bgRect =
            editingElStyle.backgroundAttachment === "fixed"
                ? iframeEl.getBoundingClientRect()
                : editingElement.getBoundingClientRect();

        if (editingElStyle.backgroundSize === "cover") {
            const renderRatio = Math.max(
                bgRect.width / naturalWidth,
                bgRect.height / naturalHeight
            );

            return {
                x: Math.round(bgRect.width - renderRatio * naturalWidth),
                y: Math.round(bgRect.height - renderRatio * naturalHeight),
            };
        }

        let [width, height] = editingElStyle.backgroundSize.split(" ");
        if (width === "auto" && (height === "auto" || !height)) {
            return {
                x: bgRect.width - naturalWidth,
                y: bgRect.height - naturalHeight,
            };
        }
        // At least one of width or height is not auto, so we can use it to
        // calculate the other if it's not set.
        [width, height] = [parseInt(width), parseInt(height)];
        return {
            x: bgRect.width - (width || (height * naturalWidth) / naturalHeight),
            y: bgRect.height - (height || (width * naturalHeight) / naturalWidth),
        };
    }
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
        value ||= "auto";
        if (styleName === "width") {
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
    static dependencies = ["overlayButtons", "history", "backgroundPositionOption"];
    setup() {
        this.withLoadingEffect = false;
    }
    async load({ editingElement }) {
        const imageEl = await loadImage(getBgImageURLFromEl(editingElement));
        // If there is a Scroll Effect, a span.s_parallax_bg inside the section
        // contains the background. Otherwise it's the section itself.
        // `targetEl` should therefore always be the section.
        let targetEl = editingElement;
        if (editingElement.matches(".s_parallax_bg")) {
            const parallaxBgParentEl = editingElement.parentElement;
            targetEl = parallaxBgParentEl.matches(".s_parallax_bg_wrap")
                ? parallaxBgParentEl.parentElement
                : parallaxBgParentEl; // <- kept for compatibility
        }
        this.dependencies.overlayButtons.hideOverlayButtonsUi();
        return new Promise((resolve) => {
            const removeOverlay = this.services.overlay.add(
                ImagePositionOverlay,
                {
                    targetEl,
                    close: (position) => {
                        removeOverlay();
                        resolve(position);
                    },
                    onDrag: (percentPosition) => {
                        editingElement.style.backgroundPosition = `${percentPosition.left}% ${percentPosition.top}%`;
                    },
                    getDelta: () =>
                        this.dependencies.backgroundPositionOption.getDelta(
                            editingElement,
                            imageEl
                        ),
                    getPosition: () => getComputedStyle(editingElement).backgroundPosition,
                    editable: this.editable,
                    history: {
                        makeSavePoint: this.dependencies.history.makeSavePoint,
                    },
                },
                { onRemove: () => this.dependencies.overlayButtons.showOverlayButtonsUi() }
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
