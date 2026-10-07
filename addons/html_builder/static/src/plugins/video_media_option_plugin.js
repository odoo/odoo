import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

class VideoMediaOptionPlugin extends Plugin {
    static id = "videoMediaOption";
    resources = {
        on_will_save_media_dialog_handlers: this.keepVideoDescription.bind(this),
    };

    /**
     * The media dialog rebuilds the video element from scratch, even when
     * only its options changed: carry the description over to the new one,
     * unless another video was chosen.
     *
     * @param {HTMLElement[]} elements the new media elements
     * @param {Object} params
     * @param {HTMLElement} [params.node] the replaced media element
     */
    keepVideoDescription(elements, { node }) {
        const description = node?.matches(".media_iframe_video") && node.getAttribute("title");
        if (!description) {
            return;
        }
        // Same url as the one the media dialog starts from.
        const { baseUrl, embedUrl, src, oeExpression } = node.dataset;
        let url = embedUrl || src || oeExpression;
        if (url?.startsWith("//")) {
            url = "https:" + url;
        }
        url = baseUrl || url;
        for (const element of elements) {
            if (element.matches(".media_iframe_video") && element.dataset.baseUrl === url) {
                element.setAttribute("title", description);
            }
        }
    }
}

registry.category("builder-plugins").add(VideoMediaOptionPlugin.id, VideoMediaOptionPlugin);
