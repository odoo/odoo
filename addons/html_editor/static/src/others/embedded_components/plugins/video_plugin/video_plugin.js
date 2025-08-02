import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { VideoSelectorDialog } from "@html_editor/others/embedded_components/plugins/video_plugin/video_selector_dialog/video_selector_dialog";
import { renderToElement } from "@web/core/utils/render";
import { isHtmlContentSupported } from "@html_editor/core/selection_plugin";

export class VideoPlugin extends Plugin {
    static id = "video";
    static dependencies = ["embeddedComponents", "dom", "selection", "link", "history", "overlay"];
    resources = {
        user_commands: [
            {
                id: "openVideoSelectorDialog",
                title: _t("Video Link"),
                description: _t("Insert a Video"),
                icon: "fa-play",
                run: () => {
                    this.openVideoSelectorDialog((media) => {
                        this.insertVideo(media);
                    });
                },
                isAvailable: isHtmlContentSupported,
            },
        ],
        powerbox_items: [
            {
                categoryId: "navigation",
                commandId: "openVideoSelectorDialog",
            },
        ],
        mount_component_handlers: this.extendEmbeddedVideoProps.bind(this),
    };

    /**
     * Inserts a video in the editor
     * @param {Object} media
     */
    insertVideo(media) {
        const videoBlock = renderToElement("html_editor.EmbeddedVideoBlueprint", {
            embeddedProps: JSON.stringify({
                videoId: media.videoId,
                platform: media.platform,
                params: media.params || {},
            }),
        });
        this.dependencies.dom.insert(videoBlock);
        this.dependencies.selection.focusEditable();
        this.dependencies.history.addStep();
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
