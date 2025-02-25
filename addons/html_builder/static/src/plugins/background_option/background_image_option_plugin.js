import { getValueFromVar } from "@html_builder/utils/utils";
import {
    backgroundImageCssToParts,
    backgroundImagePartsToCss,
    getBgImageURLFromEl,
} from "@html_builder/utils/utils_css";
import { Plugin } from "@html_editor/plugin";
import { removeOnImageChangeAttrs } from "@html_editor/utils/image_processing";
import { registry } from "@web/core/registry";
import { convertCSSColorToRgba } from "@web/core/utils/colors";
import { getBackgroundImageColor } from "./background_image_option";

// TODO: support the setTarget

class BackgroundImageOptionPlugin extends Plugin {
    static id = "backgroundImageOption";
    static dependencies = ["builderActions", "media"];
    resources = {
        builder_actions: this.getActions(),
    };
    getActions() {
        return {
            selectFilterColor: {
                apply: ({ editingElement, param, value }) => {
                    // Find the filter element.
                    let filterEl = editingElement.querySelector(":scope > .o_we_bg_filter");

                    // If the filter would be transparent, remove it / don't create it.
                    const rgba = value && convertCSSColorToRgba(value);
                    if (!value || (rgba && rgba.opacity < 0.001)) {
                        if (filterEl) {
                            filterEl.remove();
                        }
                        return;
                    }

                    // Create the filter if necessary.
                    if (!filterEl) {
                        filterEl = document.createElement("div");
                        filterEl.classList.add("o_we_bg_filter");
                        const lastBackgroundEl = this.getLastPreFilterLayerElement();
                        if (lastBackgroundEl) {
                            lastBackgroundEl.insertAdjacentElement("afterend", filterEl);
                        } else {
                            editingElement.prepend(filterEl);
                        }
                    }
                    this.dependencies.builderActions.getAction("styleAction").apply({
                        editingElement: filterEl,
                        param: "background-color",
                        value: value,
                    });
                },
                getValue: ({ editingElement }) => {
                    const filterEl = editingElement.querySelector(":scope > .o_we_bg_filter");
                    if (!filterEl) {
                        return "";
                    }
                    return this.dependencies.builderActions.getAction("styleAction").getValue({
                        editingElement: filterEl,
                        param: "background-color",
                    });
                },
            },
            toggleBgImage: {
                load: this.loadReplaceBackgroundImage.bind(this),
                apply: this.applyReplaceBackgroundImage.bind(this),
                isApplied: ({ editingElement }) => !!getBgImageURLFromEl(editingElement),
                clean: ({ editingElement }) => {
                    editingElement.querySelector(".o_we_bg_filter")?.remove();
                    this.applyReplaceBackgroundImage.bind(this)({
                        editingElement: editingElement,
                        loadResult: "",
                    });
                },
            },
            replaceBgImage: {
                load: this.loadReplaceBackgroundImage.bind(this),
                apply: this.applyReplaceBackgroundImage.bind(this),
            },
            dynamicColor: {
                getValue: ({ editingElement, param: colorName }) =>
                    getBackgroundImageColor(editingElement, colorName),
                apply: ({ editingElement, param: colorName, value }) => {
                    value = getValueFromVar(value);
                    const currentSrc = getBgImageURLFromEl(editingElement);
                    const newURL = new URL(currentSrc, window.location.origin);
                    newURL.searchParams.set(colorName, value);
                    const src = newURL.pathname + newURL.search;
                    this.setImageBackground(editingElement, src);
                },
            },
        };
    }
    loadReplaceBackgroundImage() {
        return new Promise((resolve) => {
            const onClose = this.dependencies.media.openMediaDialog({
                onlyImages: true,
                save: (imageEl) => {
                    resolve(imageEl.getAttribute("src"));
                },
            });
            onClose.then(resolve);
        });
    }
    applyReplaceBackgroundImage({ editingElement, loadResult: imageSrc }) {
        if (!imageSrc) {
            return;
        }
        this.setImageBackground(editingElement, imageSrc);
        for (const attr of removeOnImageChangeAttrs) {
            delete editingElement.dataset[attr];
        }
        // TODO: call _autoOptimizeImage of the ImageHandlersOption
    }
    /**
     *
     * @param {HTMLElement} editingElement
     * @param {String} backgroundURL
     */
    setImageBackground(editingElement, backgroundURL) {
        const parts = backgroundImageCssToParts(editingElement.style["background-image"]);
        if (backgroundURL) {
            parts.url = `url('${backgroundURL}')`;
            editingElement.classList.add("oe_img_bg", "o_bg_img_center");
        } else {
            delete parts.url;
            editingElement.classList.remove(
                "oe_img_bg",
                "o_bg_img_center",
                "o_modified_image_to_save"
            );
        }
        const combined = backgroundImagePartsToCss(parts);
        // TODO: check this comment
        // We use selectStyle so that if when a background image is removed the
        // remaining image matches the o_cc's gradient background, it can be
        // removed too.
        this.dependencies.builderActions.getAction("styleAction").apply({
            editingElement: editingElement,
            param: "background-image",
            value: combined,
        });
    }
    getLastPreFilterLayerElement() {
        return null;
    }
}

registry
    .category("website-plugins")
    .add(BackgroundImageOptionPlugin.id, BackgroundImageOptionPlugin);
