import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { withSequence } from "@html_editor/utils/resource";
import { BuilderAction } from "@html_builder/core/builder_action";
import { _t } from "@web/core/l10n/translation";
import { VideoSelector } from "@html_editor/main/media/media_dialog/video_selector";

/**
 * @typedef { Object } WebsiteBackgroundVideoShared
 * @property { WebsiteBackgroundVideoPlugin['loadReplaceBackgroundVideo'] } loadReplaceBackgroundVideo
 * @property { WebsiteBackgroundVideoPlugin['applyReplaceBackgroundVideo'] } applyReplaceBackgroundVideo
 */

function getBgVideoOrParallax(editingElement) {
    // Make sure parallax and video element are considered to be below the
    // color filters / shape
    const bgVideoEl = editingElement.querySelector(":scope > .o_bg_video_container");
    if (bgVideoEl) {
        return bgVideoEl;
    }
    return editingElement.querySelector(":scope > .s_parallax_bg");
}

class WebsiteBackgroundImageOptionPlugin extends Plugin {
    static id = "websiteBackgroundImageOptionPlugin";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        background_filter_target_providers: withSequence(10, getBgVideoOrParallax),
    };
}

class WebsiteBackgroundShapeOptionPlugin extends Plugin {
    static id = "websiteBackgroundShapeOptionPlugin";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        background_shape_target_providers: withSequence(10, getBgVideoOrParallax),
    };
}

class WebsiteBackgroundVideoPlugin extends Plugin {
    static id = "websiteBackgroundVideoPlugin";
    static dependencies = ["media"];
    static shared = [
        "loadReplaceBackgroundVideo",
        "applyReplaceBackgroundVideo",
        "removeBackgroundVideo",
    ];
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_actions: {
            ToggleBgVideoAction,
            RemoveBgVideoAction,
            ReplaceBgVideoAction,
        },
        system_node_selectors: ".o_bg_video_container",
    };
    loadReplaceBackgroundVideo() {
        return new Promise((resolve) => {
            const onClose = this.dependencies.media.openMediaDialog({
                extraTabs: [
                    {
                        id: "VIDEO_BACKGROUND",
                        title: _t("Videos"),
                        Component: VideoSelector,
                        props: {
                            isForBgVideo: true,
                            vimeoPreviewIds: [
                                "528686125",
                                "430330731",
                                "509869821",
                                "397142251",
                                "763851966",
                                "486931161",
                                "499761556",
                                "1092009120",
                                "728584384",
                                "865314310",
                                "511727912",
                                "466830211",
                            ],
                        },
                    },
                ],
                visibleTabs: ["VIDEO_BACKGROUND"],
                save: (media) => {
                    resolve(media.querySelector("iframe").src);
                },
            });
            onClose.then(resolve);
        });
    }
    applyReplaceBackgroundVideo({
        editingElement,
        loadResult: mediaSrc,
        params: { forceClean = false },
    }) {
        if (!forceClean && !mediaSrc) {
            // No video has been chosen by the user on the media dialog
            return;
        }
        editingElement.classList.toggle("o_background_video", !!mediaSrc);
        if (mediaSrc) {
            editingElement.dataset.bgVideoSrc = mediaSrc;
        } else {
            delete editingElement.dataset.bgVideoSrc;
        }
    }
    /**
     * Remove the current background video and notify listeners.
     *
     * @param {Object} context
     * @param {HTMLElement} context.editingElement
     * @param {Object} [context.params]
     */
    removeBackgroundVideo({ editingElement, params }) {
        editingElement.querySelector(":scope > .o_we_bg_filter")?.remove();
        this.applyReplaceBackgroundVideo({
            editingElement,
            loadResult: "",
            params: { ...params, forceClean: true },
        });
        this.dispatchTo("on_bg_image_hide_handlers", editingElement);
    }
}

export class ToggleBgVideoAction extends BuilderAction {
    static id = "toggleBgVideo";
    static dependencies = ["websiteBackgroundVideoPlugin"];
    load(context) {
        return this.dependencies.websiteBackgroundVideoPlugin.loadReplaceBackgroundVideo(context);
    }
    apply({ editingElement, params, loadResult }) {
        this.dependencies.websiteBackgroundVideoPlugin.applyReplaceBackgroundVideo({
            editingElement: editingElement,
            params: params,
            loadResult: loadResult,
        });
        this.dispatchTo("on_bg_image_hide_handlers", editingElement);
    }
    isApplied({ editingElement }) {
        return editingElement.classList.contains("o_background_video");
    }
    clean(context) {
        this.dependencies.websiteBackgroundVideoPlugin.removeBackgroundVideo(context);
    }
}

export class RemoveBgVideoAction extends BuilderAction {
    static id = "removeBgVideo";
    static dependencies = ["websiteBackgroundVideoPlugin"];
    apply(context) {
        this.dependencies.websiteBackgroundVideoPlugin.removeBackgroundVideo(context);
    }
}

export class ReplaceBgVideoAction extends BuilderAction {
    static id = "replaceBgVideo";
    static dependencies = ["websiteBackgroundVideoPlugin"];
    load(context) {
        return this.dependencies.websiteBackgroundVideoPlugin.loadReplaceBackgroundVideo(context);
    }
    apply(context) {
        return this.dependencies.websiteBackgroundVideoPlugin.applyReplaceBackgroundVideo(context);
    }
}

registry
    .category("website-plugins")
    .add(WebsiteBackgroundVideoPlugin.id, WebsiteBackgroundVideoPlugin);

registry
    .category("website-plugins")
    .add(WebsiteBackgroundImageOptionPlugin.id, WebsiteBackgroundImageOptionPlugin);

registry
    .category("website-plugins")
    .add(WebsiteBackgroundShapeOptionPlugin.id, WebsiteBackgroundShapeOptionPlugin);
