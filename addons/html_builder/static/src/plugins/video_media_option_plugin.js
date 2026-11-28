import { Plugin } from "@html_editor/plugin";
import { PLATFORMS } from "@html_editor/main/media/media_dialog/video_selector";
import { registry } from "@web/core/registry";

class VideoMediaOptionPlugin extends Plugin {
    static id = "videoMediaOption";
    resources = {
        on_will_save_media_dialog_handlers: this.setVideoDescription.bind(this),
    };

    /**
     * The media dialog rebuilds the video element from scratch, even when
     * only its options changed: carry the description over to the new one.
     * For a new video, use its title as the default description.
     *
     * @param {HTMLElement[]} elements the new media elements
     * @param {Object} params
     * @param {HTMLElement} [params.node] the replaced media element
     */
    async setVideoDescription(elements, { node }) {
        const description = node?.matches(".media_iframe_video") && node.dataset.videoDescription;
        const { baseUrl, oeExpression } = node?.dataset || {};
        const url = baseUrl || (oeExpression && "https:" + oeExpression);
        for (const element of elements) {
            if (!element.matches(".media_iframe_video")) {
                continue;
            }
            // Same url: the user kept the same video.
            if (description && element.dataset.baseUrl === url) {
                element.dataset.videoDescription = description;
                continue;
            }
            const title = await PLATFORMS[element.dataset.platform]
                ?.getTitle(element.dataset.videoId)
                .catch(() => "");
            if (title) {
                element.dataset.videoDescription = title;
            }
        }
    }
}

registry.category("builder-plugins").add(VideoMediaOptionPlugin.id, VideoMediaOptionPlugin);
