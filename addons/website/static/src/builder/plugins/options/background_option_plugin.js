import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { withSequence } from "@html_editor/utils/resource";

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
    resources = {
        background_filter_target_providers: withSequence(10, getBgVideoOrParallax),
    };
}

class WebsiteBackgroundShapeOptionPlugin extends Plugin {
    static id = "websiteBackgroundShapeOptionPlugin";
    resources = {
        background_shape_target_providers: withSequence(10, getBgVideoOrParallax),
    };
}

class WebsiteBackgroundVideoPlugin extends Plugin {
    static id = "websiteBackgroundVideoPlugin";
    static dependencies = ["media"];
    resources = {
        builder_actions: this.getActions(),
    };
    getActions() {
        return {
            toggleBgVideo: {
                load: this.loadReplaceBackgroundVideo.bind(this),
                apply: ({ editingElement, params, loadResult }) => {
                    this.applyReplaceBackgroundVideo({
                        editingElement: editingElement,
                        params: params,
                        loadResult: loadResult,
                    });
                    this.dispatchTo("on_bg_image_hide_handlers", editingElement);
                },
                isApplied: ({ editingElement }) =>
                    editingElement.classList.contains("o_background_video"),
                clean: ({ editingElement }) => {
                    editingElement.querySelector(":scope > .o_we_bg_filter")?.remove();
                    this.applyReplaceBackgroundVideo({
                        editingElement: editingElement,
                        loadResult: "",
                        params: { forceClean: true },
                    });
                },
            },
            replaceBgVideo: {
                load: this.loadReplaceBackgroundVideo.bind(this),
                apply: this.applyReplaceBackgroundVideo.bind(this),
            },
        };
    }
    loadReplaceBackgroundVideo() {
        return new Promise((resolve) => {
            const onClose = this.dependencies.media.openMediaDialog({
                noIcons: true,
                noImages: true,
                noDocuments: true,
                isForBgVideo: true,
                vimeoPreviewIds: ['528686125', '430330731', '509869821', '397142251', '763851966', '486931161',
                    '499761556', '392935303', '728584384', '865314310', '511727912', '466830211'],
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
