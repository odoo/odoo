import { VideoSelector } from "@html_editor/main/media/media_dialog/video_selector";
import { renderToElement } from "@web/core/utils/render";

export class EmbeddedVideoSelector extends VideoSelector {
    /** @override */
    static mediaSpecificClasses = [];

    /** @override */
    static createElements(selectedMedia) {
        return selectedMedia.map((media) =>
            renderToElement("html_editor.EmbeddedVideoBlueprint", {
                embeddedProps: JSON.stringify({
                    videoId: media.videoId,
                    platform: media.platform,
                    params: media.params || {},
                }),
            })
        );
    }
}
