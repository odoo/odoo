import { VideoPlugin } from "@html_editor/main/media/video_plugin";
import { VideoSelectorDialog } from "@html_editor/others/embedded_components/plugins/video_plugin/video_selector_dialog/video_selector_dialog";
import { EmbeddedVideoSelector } from "./video_selector_dialog/embedded_video_selector";

/**
 * This plugin is meant to replace the Video plugin.
 */
export class EmbeddedVideoPlugin extends VideoPlugin {
    static id = "embeddedVideo";
    static dependencies = ["embeddedComponents", "selection", "history", "overlay"];

    // Extends the base class resources
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
     * Inserts a dialog allowing the user to insert a video
     * @param {function} save
     * @param {HTMLIFrameElement} iframe
     */
    openVideoSelectorDialog(save, iframe) {
        const selection = this.dependencies.selection.getEditableSelection();
        let restoreSelection = () => {
            this.dependencies.selection.setSelection(selection);
        };
        this.services.dialog.add(
            VideoSelectorDialog,
            {
                save: (media) => {
                    save(media);
                    restoreSelection = () => {};
                },
                ...(iframe && { videoIframe: iframe }),
            },
            {
                onClose: () => {
                    restoreSelection();
                },
            }
        );
    }
}
