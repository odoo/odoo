import { VideoSelector } from "@html_editor/main/media/media_dialog/video_selector";
import { renderToElement } from "@web/core/utils/render";

export class EmbeddedVideoSelector extends VideoSelector {
    /** @override */
    static mediaSpecificClasses = [];

    /** @override */
    static createElements(selectedVideos, { document = window.document } = {}) {
        return selectedVideos.map((videoData) => {
            const videoElement = renderToElement("html_editor.EmbeddedVideoBlueprint", {
                embeddedProps: JSON.stringify({
                    baseUrl: videoData.baseUrl || "",
                    videoId: videoData.videoId,
                    platform: videoData.platform,
                    params: videoData.options || {},
                }),
                isVertical: videoData.options?.isVertical || false,
            });
            return document.importNode(videoElement, true);
        });
    }
}
