import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { CoverPropertiesOption } from "@website/builder/plugins/options/cover_properties_option";
import { BuilderAction } from "@html_builder/core/builder_action";
import { rpc } from "@web/core/network/rpc";
import { withSequence } from "@html_editor/utils/resource";
import { COVER_PROPERTIES } from "@website/builder/option_sequence";
import { coverSizeClassLabels } from "./cover_properties_option";

class CoverPropertiesOptionPlugin extends Plugin {
    static id = "coverPropertiesOption";
    static dependencies = ["builderActions", "media", "imagePostProcess"];
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_options: [withSequence(COVER_PROPERTIES, CoverPropertiesOption)],
        builder_actions: { SetCoverBackgroundAction },
        before_save_handlers: this.savePendingBackgroundImage.bind(this),
        dirt_marks: {
            id: "cover-props",
            setDirtyOnMutation: (record) => {
                // based on what will be read with readCoverPoperties
                if (
                    record.target.matches?.(".o_record_cover_image, .o_record_cover_filter") &&
                    record.attributeName === "style"
                ) {
                    return record.target.closest(".o_record_cover_container");
                }
                if (
                    record.target.classList?.contains("o_record_cover_container") &&
                    (record.attributeName === "style" || record.type === "classList")
                ) {
                    return record.target;
                }
            },
            save: (el) =>
                this.services.orm.write(el.dataset.resModel, [Number(el.dataset.resId)], {
                    cover_properties: JSON.stringify(this.readCoverPoperties(el)),
                }),
        },
    };

    async savePendingBackgroundImage(editableEl = this.editable) {
        for (const coverEl of editableEl.querySelectorAll(".o_record_cover_container")) {
            const bgEl = coverEl.querySelector(".o_record_cover_image");
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
                        name: `${modelName} ${recordName} cover image.${
                            groups.mimetype.split("/")[1]
                        }`,
                        data: groups.imageData,
                        is_image: true,
                        res_model: "ir.ui.view",
                    });
                    bgEl.style.backgroundImage = `url(${attachment.image_src})`;
                }
                bgEl.classList.remove("o_b64_cover_image_to_save");
            }
        }
    }

    readCoverPoperties(el) {
        const coverProperties = {};
        const bg = el.querySelector(".o_record_cover_image")?.style.backgroundImage || "";
        coverProperties["background-image"] = bg;

        // TODO: `o_record_has_cover` should be handled using model field, not
        // resize_class to avoid all of this.
        let coverClass = Object.keys(coverSizeClassLabels).find((e) => el.classList.contains(e));
        if (bg && bg !== "none") {
            coverClass += " o_record_has_cover";
        }
        coverProperties.resize_class = coverClass;

        coverProperties.text_align_class =
            ["text-center", "text-end"].find((e) => el.classList.contains(e)) || "";

        coverProperties.opacity = el.querySelector(".o_record_cover_filter")?.style.opacity || 0.0;

        coverProperties.background_color_class = [...el.classList.values()]
            .filter((e) => e.startsWith("bg-") || e.startsWith("o_cc"))
            .join(" ");
        if (el.style.backgroundImage) {
            coverProperties.background_color_style = `background-color: rgba(0, 0, 0, 0); background-image: ${el.style.backgroundImage};`;
        } else if (el.style.backgroundColor) {
            coverProperties.background_color_style = `background-color: ${el.style.backgroundColor};`;
        } else {
            coverProperties.background_color_style = "";
        }
        return coverProperties;
    }
}

export class SetCoverBackgroundAction extends BuilderAction {
    static id = "setCoverBackground";
    static dependencies = ["builderActions", "media"];
    setup() {
        this.classAction = this.dependencies.builderActions.getAction("classAction");
        this.styleAction = this.dependencies.builderActions.getAction("styleAction");
    }
    load({ params: { mainParam: setBackground } }) {
        if (!setBackground) {
            return;
        }
        let resultPromise;
        return this.dependencies.media
            .openMediaDialog({
                onlyImages: true,
                save: (imageEl) => {
                    resultPromise = (async () => {
                        const b64ToSave = imageEl.getAttribute("src").startsWith("data:");
                        return { imageSrc: imageEl.getAttribute("src"), b64ToSave };
                    })();
                },
            })
            .then(() => resultPromise || { cancel: true });
    }

    isApplied({ editingElement, params: { mainParam: setBackground } }) {
        const bg = editingElement.querySelector(".o_record_cover_image").style.backgroundImage;
        return !setBackground === (!bg || bg === "none");
    }
    apply({ editingElement, loadResult: { imageSrc, b64ToSave, cancel } = {} }) {
        if (cancel) {
            return;
        }
        (imageSrc ? this.classAction.apply : this.classAction.clean)({
            editingElement,
            params: { mainParam: "o_record_has_cover" },
        });

        const bgEl = editingElement.querySelector(".o_record_cover_image");

        (b64ToSave ? this.classAction.apply : this.classAction.clean)({
            editingElement: bgEl,
            params: { mainParam: "o_b64_cover_image_to_save" },
        });

        this.styleAction.apply({
            editingElement: bgEl,
            params: { mainParam: "background-image" },
            value: imageSrc ? `url('${imageSrc}')` : "",
        });
    }
}

registry
    .category("website-plugins")
    .add(CoverPropertiesOptionPlugin.id, CoverPropertiesOptionPlugin);
