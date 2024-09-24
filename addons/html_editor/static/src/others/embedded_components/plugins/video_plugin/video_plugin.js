import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { VideoSelectorDialog } from "@html_editor/others/embedded_components/plugins/video_plugin/video_selector_dialog/video_selector_dialog";
import { renderToElement } from "@web/core/utils/render";

export class VideoPlugin extends Plugin {
    static name = "video";
    static dependencies = ["embedded_components", "dom", "selection", "link"];
    resources = {
        powerboxItems: [
            {
                category: "navigation",
                name: _t("Video Link"),
                priority: 70,
                description: _t("Insert a Video"),
                fontawesome: "fa-play",
                action: () => {
                    this.openVideoSelectorDialog((media) => {
                        this.insertVideo(media);
                    });
                },
            },
        ],
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
        this.shared.domInsert(videoBlock);
        this.dispatch("ADD_STEP");
    }

    /**
     * Inserts a dialog allowing the user to insert a video
     * @param {function} save
     */
    openVideoSelectorDialog(save) {
        const selection = this.shared.getEditableSelection();
        let restoreSelection = () => {
            this.shared.setSelection(selection);
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
