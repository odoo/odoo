import { VideoPlugin } from "@html_editor/main/media/video_plugin";
import { EmbeddedVideoSelector } from "./video_selector_dialog/embedded_video_selector";

/**
 * This plugin is meant to replace the Video plugin.
 */
export class EmbeddedVideoPlugin extends VideoPlugin {
    static id = "embeddedVideo";
    static dependencies = ["embeddedComponents", "selection", "history", "overlay", "media"];

    // Extends the base class resources
    /** @type {import("plugins").EditorResources} */
    resources = {
        ...this.resources,
        mount_component_handlers: this.extendEmbeddedVideoProps.bind(this),
    };

    /** @override */
    get componentForMediaDialog() {
        return EmbeddedVideoSelector;
    }

    /**
     * @param {Object} props
     */
    extendEmbeddedVideoProps({ name, props }) {
        if (name === "video") {
            Object.assign(props, {
                createOverlay: (Component, props = {}, options) =>
                    this.dependencies.overlay.createOverlay(Component, props, options),
                focusEditable: () => this.dependencies.selection.focusEditable(),
                addStep: () => this.dependencies.history.addStep(),
                openVideoSelectorDialog: (save, media) => {
                    this.openVideoSelectorDialog(save, media);
                },
            });
        }
    }

    /**
     * Open media dialog allowing the user to insert a video
     * @param {function} save
     * @param {HTMLIFrameElement} iframe
     */
    openVideoSelectorDialog(save, iframe) {
        this.dependencies.media.openMediaDialog({
            node: iframe,
            save: (elements, [media]) => {
                if (media.src) {
                    save(media);
                }
            },
            visibleTabs: ["VIDEOS"],
        });
    }
}
