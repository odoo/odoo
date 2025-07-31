import { VideoPlugin } from "@html_editor/main/media/video_plugin";
import { EmbeddedVideoSelector } from "./video_selector_dialog/embedded_video_selector";

/**
 * This plugin is meant to replace the Video plugin.
 */
export class EmbeddedVideoPlugin extends VideoPlugin {
    static id = "embeddedVideo";
    static dependencies = ["embeddedComponents"];

    /** @override */
    get componentForMediaDialog() {
        return EmbeddedVideoSelector;
    }
}
