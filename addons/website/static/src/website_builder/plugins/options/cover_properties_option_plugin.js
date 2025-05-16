import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { CoverPropertiesOption } from "@website/website_builder/plugins/options/cover_properties_option";
import { classAction } from "@html_builder/core/core_builder_action_plugin";
import { loadImageInfo } from "@html_editor/utils/image_processing";
import { rpc } from "@web/core/network/rpc";
import { withSequence } from "@html_editor/utils/resource";
import { COVER_PROPERTIES } from "@website/website_builder/option_sequence";

class CoverPropertiesOptionPlugin extends Plugin {
    static id = "coverPropertiesOption";
    static dependencies = ["builderActions", "media", "imagePostProcess"];
    resources = {
        builder_options: [
            withSequence(COVER_PROPERTIES, {
                OptionComponent: CoverPropertiesOption,
                selector: ".o_record_cover_container",
                editableOnly: false,
            }),
        ],
        builder_actions: {
            setCoverBackground: {
                load: this.loadBackgroundImage.bind(this),
                isApplied: ({ editingElement, params: { mainParam: setBackground } }) => {
                    const bg =
                        editingElement.querySelector(".o_record_cover_image").style.backgroundImage;
                    return !setBackground === (!bg || bg === "none");
                },
                apply: this.applyBackgroundImage.bind(this),
            },
        },
        before_save_handlers: this.savePendingBackgroundImage.bind(this),
        clean_for_save_handlers: this.saveToDataset.bind(this),
    };

    loadBackgroundImage({ params: { mainParam: setBackground } }) {
        if (!setBackground) {
            return;
        }
        let resultPromise;
        return this.dependencies.media
            .openMediaDialog({
                onlyImages: true,
                save: (imageEl) => {
                    resultPromise = (async () => {
                        Object.assign(imageEl.dataset, await loadImageInfo(imageEl));
                        let b64ToSave = false;
                        if (
                            imageEl.dataset.mimetypeBeforeConversion &&
                            !["image/gif", "image/svg+xml", "image/webp"].includes(
                                imageEl.dataset.mimetypeBeforeConversion
                            )
                        ) {
                            // Convert to webp but keep original width.
                            const updateImgAttributes =
                                await this.dependencies.imagePostProcess.processImage(imageEl, {
                                    formatMimetype: "image/webp",
                                });
                            updateImgAttributes();
                            b64ToSave = true;
                        }
                        return { imageSrc: imageEl.getAttribute("src"), b64ToSave };
                    })();
                },
            })
            .then(() => resultPromise || { cancel: true });
    }

    applyBackgroundImage({ editingElement, loadResult: { imageSrc, b64ToSave, cancel } = {} }) {
        if (cancel) {
            return;
        }
        (imageSrc ? classAction.apply : classAction.clean)({
            editingElement,
            params: { mainParam: "o_record_has_cover" },
        });

        const bgEl = editingElement.querySelector(".o_record_cover_image");

        (b64ToSave ? classAction.apply : classAction.clean)({
            editingElement: bgEl,
            params: { mainParam: "o_b64_cover_image_to_save" },
        });

        this.dependencies.builderActions.getAction("styleAction").apply({
            editingElement: bgEl,
            params: { mainParam: "background-image" },
            value: imageSrc ? `url('${imageSrc}')` : "",
        });
    }

    async savePendingBackgroundImage(editableEl = this.editable) {
        const coverEl = editableEl.querySelector(".o_record_cover_container");
        const bgEl = coverEl?.querySelector(".o_record_cover_image");
        const bgImage = bgEl?.style.backgroundImage;
        if (bgImage && bgEl.classList.contains("o_b64_cover_image_to_save")) {
            const resModel = coverEl.dataset.resModel;
            const resID = Number(coverEl.dataset.resId);
            if (!resModel || !resID) {
                throw new Error("There should be a model and id associated to the cover");
            }

            // Checks if the image is in base64 format for RPC call. Relying
            // only on the presence of the class "o_b64_cover_image_to_save" is not
            // robust enough.
            const groups = bgImage.match(
                /url\("data:(?<mimetype>.*);base64,(?<imageData>.*)"\)/
            )?.groups;
            if (groups?.imageData) {
                const modelName = await this.services.website.getUserModelName(resModel);
                const recordNameEl = bgEl
                    .closest("body")
                    .querySelector(
                        `[data-oe-model="${resModel}"][data-oe-id="${resID}"][data-oe-field="name"]`
                    );
                const recordName = recordNameEl
                    ? `'${recordNameEl.textContent.replaceAll("/", "")}'`
                    : resID;
                const attachment = await rpc("/web_editor/attachment/add_data", {
                    name: `${modelName} ${recordName} cover image.${groups.mimetype.split("/")[1]}`,
                    data: groups.imageData,
                    is_image: true,
                    res_model: "ir.ui.view",
                });
                bgEl.style.backgroundImage = `url(${attachment.image_src})`;
            }
            bgEl.classList.remove("o_b64_cover_image_to_save");
        }
    }

    /**
     * Updates the cover properties dataset used for saving.
     */
    saveToDataset({ root }) {
        if (root.matches(".o_record_cover_container")) {
            const bg = root.querySelector(".o_record_cover_image")?.style.backgroundImage || "";
            root.dataset.bgImage = bg;

            // TODO: `o_record_has_cover` should be handled using model field, not
            // resize_class to avoid all of this.
            let coverClass = ["o_full_screen_height", "o_half_screen_height", "cover_auto"].find(
                (e) => root.classList.contains(e)
            );
            if (bg && bg !== "none") {
                coverClass += " o_record_has_cover";
            }
            root.dataset.coverClass = coverClass;

            root.dataset.textAlignClass =
                ["text-center", "text-end"].find((e) => root.classList.contains(e)) || "";

            root.dataset.filterValue =
                root.querySelector(".o_record_cover_filter")?.style.opacity || 0.0;

            root.dataset.bgColorClass = [...root.classList.values()]
                .filter((e) => e.startsWith("bg-") || e.startsWith("o_cc"))
                .join(" ");
            if (root.style.backgroundImage) {
                root.dataset.bgColorStyle = `background-color: rgba(0, 0, 0, 0); background-image: ${root.style.backgroundImage};`;
            } else if (root.style.backgroundColor) {
                root.dataset.bgColorStyle = `background-color: ${root.style.backgroundColor};`;
            } else {
                root.dataset.bgColorStyle = "";
            }
        }
    }
}
registry
    .category("website-plugins")
    .add(CoverPropertiesOptionPlugin.id, CoverPropertiesOptionPlugin);
