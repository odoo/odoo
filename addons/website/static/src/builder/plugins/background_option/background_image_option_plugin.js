import { getValueFromVar } from "@html_builder/utils/utils";
import { getBgImageURLFromEl, isBackgroundImageAttribute } from "@html_builder/utils/utils_css";
import { Plugin } from "@html_editor/plugin";
import { removeOnImageChangeAttrs } from "@html_editor/utils/image_processing";
import { registry } from "@web/core/registry";
import { convertCSSColorToRgba } from "@web/core/utils/colors";
import { getBackgroundImageColor } from "./background_image_option";

export class BackgroundImageOptionPlugin extends Plugin {
    static id = "backgroundImageOption";
    static dependencies = ["builderActions", "media", "style"];
    static shared = ["changeEditingEl", "setImageBackground"];
    resources = {
        builder_actions: this.getActions(),
    };
    getActions() {
        return {
            selectFilterColor: {
                apply: ({ editingElement, value }) => {
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
                        let lastBackgroundEl;
                        for (const fn of this.getResource("background_filter_target_providers")) {
                            lastBackgroundEl = fn(editingElement);
                            if (lastBackgroundEl) {
                                break;
                            }
                        }
                        if (lastBackgroundEl) {
                            lastBackgroundEl.insertAdjacentElement("afterend", filterEl);
                        } else {
                            editingElement.prepend(filterEl);
                        }
                    }
                    this.dependencies.builderActions.getAction("styleAction").apply({
                        editingElement: filterEl,
                        params: {
                            mainParam: "background-color",
                        },
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
                        params: {
                            mainParam: "background-color",
                        },
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
                        loadResult: undefined,
                        params: { forceClean: true },
                    });
                    this.dispatchTo("on_bg_image_hide_handlers", editingElement);
                },
            },
            replaceBgImage: {
                load: this.loadReplaceBackgroundImage.bind(this),
                apply: this.applyReplaceBackgroundImage.bind(this),
            },
            dynamicColor: {
                getValue: ({ editingElement, params: { mainParam: colorName } }) =>
                    getBackgroundImageColor(editingElement, colorName),
                apply: ({ editingElement, params: { mainParam: colorName }, value }) => {
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
    /**
     * Transfers the background-image and the dataset information relative to
     * this image from the old editing element to the new one.
     * @param {HTMLElement} oldEditingEl - The old editing element.
     * @param {HTMLElement} newEditingEl - The new editing element.
     */
    changeEditingEl(oldEditingEl, newEditingEl) {
        // When we change the target of this option we need to transfer the
        // background-image and the dataset information relative to this image
        // from the old target to the new one.
        const oldBgURL = getBgImageURLFromEl(oldEditingEl);
        const isModifiedImage = oldEditingEl.classList.contains("o_modified_image_to_save");
        const filteredOldDataset = Object.entries(oldEditingEl.dataset).filter(([key]) =>
            isBackgroundImageAttribute(key)
        );
        // Delete the dataset information relative to the background-image of
        // the old target.
        for (const [key] of filteredOldDataset) {
            delete oldEditingEl.dataset[key];
        }
        // It is important to delete ".o_modified_image_to_save" from the old
        // target as its image source will be deleted.
        oldEditingEl.classList.remove("o_modified_image_to_save");
        this.setImageBackground(oldEditingEl, "");
        // Apply the changes on the new editing element
        if (oldBgURL) {
            this.setImageBackground(newEditingEl, oldBgURL);
            for (const [key, value] of filteredOldDataset) {
                newEditingEl.dataset[key] = value;
            }
            newEditingEl.classList.toggle("o_modified_image_to_save", isModifiedImage);
        }
    }
    loadReplaceBackgroundImage({ editingElement }) {
        return new Promise((resolve) => {
            const onClose = this.dependencies.media.openMediaDialog({
                onlyImages: true,
                node: editingElement,
                save: async (imageEl) => {
                    resolve(imageEl);
                },
            });
            onClose.then(resolve);
        });
    }
    applyReplaceBackgroundImage({
        editingElement,
        loadResult: imageEl,
        params: { forceClean = false },
    }) {
        if (!forceClean && !imageEl) {
            // Do nothing: no images has been selected on the media dialog
            return;
        }
        const src = imageEl?.src || "";
        this.setImageBackground(editingElement, src);
        for (const attr of removeOnImageChangeAttrs) {
            delete editingElement.dataset[attr];
        }
        if (imageEl) {
            if (src.startsWith("data:")) {
                editingElement.classList.add("o_modified_image_to_save");
            }
            Object.assign(editingElement.dataset, imageEl.dataset);
        }
    }
    /**
     *
     * @param {HTMLElement} el
     * @param {String} backgroundURL
     */
    setImageBackground(el, backgroundURL) {
        if (backgroundURL) {
            el.classList.add("oe_img_bg", "o_bg_img_center", "o_bg_img_origin_border_box");
        } else {
            el.classList.remove(
                "oe_img_bg",
                "o_bg_img_center",
                "o_bg_img_origin_border_box",
                "o_modified_image_to_save"
            );
        }
        // TODO: check this comment
        // We use selectStyle so that if when a background image is removed the
        // remaining image matches the o_cc's gradient background, it can be
        // removed too.
        this.dependencies.style.setBackgroundImageUrl(el, backgroundURL);
    }
}

registry
    .category("website-plugins")
    .add(BackgroundImageOptionPlugin.id, BackgroundImageOptionPlugin);
