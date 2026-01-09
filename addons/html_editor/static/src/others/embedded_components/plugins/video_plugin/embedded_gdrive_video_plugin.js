import { EmbeddedVideoSelector } from "./video_selector_dialog/embedded_video_selector";
import { GDriveVideoPlugin } from "@html_editor/main/media/video/gdrive_video_plugin";

export class EmbeddedGDriveVideoPlugin extends GDriveVideoPlugin {
    static id = "embeddedGDriveVideo";
    static dependencies = [...super.dependencies, "embeddedComponents"];

    /** @override */
    createVideoElement(videoData) {
        const { video_id: videoId, platform, params } = videoData;
        return EmbeddedVideoSelector.createElements([{ videoId, platform, params }])[0];
    }
}
