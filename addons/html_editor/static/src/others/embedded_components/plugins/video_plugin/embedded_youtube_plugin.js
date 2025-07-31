import { YoutubePlugin } from "@html_editor/main/youtube_plugin";
import { EmbeddedVideoSelector } from "./video_selector_dialog/embedded_video_selector";

export class EmbeddedYoutubePlugin extends YoutubePlugin {
    static id = "embeddedYoutube";
    static dependencies = [...super.dependencies, "embeddedComponents"];

    /** @override */
    createVideoElement(videoData) {
        const { video_id: videoId, platform, params } = videoData;
        return EmbeddedVideoSelector.createElements([{ videoId, platform, params }])[0];
    }
}
