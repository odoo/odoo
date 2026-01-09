import { EmbeddedVideoSelector } from "./video_selector_dialog/embedded_video_selector";
import { LoomPlugin } from "@html_editor/main/media/video/loom_plugin";

export class EmbeddedLoomPlugin extends LoomPlugin {
    static id = "embeddedLoomVideo";
    static dependencies = [...super.dependencies, "embeddedComponents"];

    /** @override */
    createVideoElement(videoData) {
        const { video_id: videoId, platform, params } = videoData;
        return EmbeddedVideoSelector.createElements([{ videoId, platform, params }])[0];
    }
}
