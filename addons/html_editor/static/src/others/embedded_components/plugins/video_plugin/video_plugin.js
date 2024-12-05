import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { VideoSelectorDialog } from "@html_editor/others/embedded_components/plugins/video_plugin/video_selector_dialog/video_selector_dialog";
import { renderToElement } from "@web/core/utils/render";

export class VideoPlugin extends Plugin {
    static id = "video";
    static dependencies = ["embeddedComponents", "dom", "selection", "link", "history"];
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
            },
        ],
        powerbox_items: [
            {
                categoryId: "navigation",
                commandId: "openVideoSelectorDialog",
            },
        ],
    };

    /**
     * Inserts a video in the editor
     * @param {Object} media
     */
    insertVideo(media) {
        const videoBlock = renderToElement(
            "html_editor.EmbeddedVideoBlueprint",
            {
                embeddedProps: JSON.stringify({
                    videoId: media.videoId,
                    platform: media.platform,
                    params: media.params || {},
                }),
            },
            {
                document: this.document,
            }
        );
        this.dependencies.dom.insert(videoBlock);
        this.dependencies.history.addStep();
    }

    /**
     * Inserts a dialog allowing the user to insert a video
     * @param {function} save
     */
    openVideoSelectorDialog(save) {
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
            },
            {
                onClose: () => {
                    restoreSelection();
                },
            }
        );
    }
}
