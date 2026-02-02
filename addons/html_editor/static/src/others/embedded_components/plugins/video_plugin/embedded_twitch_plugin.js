import { EmbeddedVideoSelector } from "./video_selector_dialog/embedded_video_selector";
import { TwitchPlugin } from "@html_editor/main/media/video/twitch_plugin";

export class EmbeddedTwitchPlugin extends TwitchPlugin {
    static id = "embeddedTwitchVideo";
    static dependencies = [...super.dependencies, "embeddedComponents"];

    /** @override */
    createVideoElement(videoData) {
        const { video_id: videoId, platform, params } = videoData;
        return EmbeddedVideoSelector.createElements([{ videoId, platform, params }])[0];
    }
}
