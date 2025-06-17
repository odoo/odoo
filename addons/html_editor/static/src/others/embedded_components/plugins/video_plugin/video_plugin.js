import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { VideoSelectorDialog } from "@html_editor/others/embedded_components/plugins/video_plugin/video_selector_dialog/video_selector_dialog";
import { renderToElement } from "@web/core/utils/render";
import { VideoSettings } from "../../core/video/video";

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
            },
        ],
        powerbox_items: [
            {
                categoryId: "navigation",
                commandId: "openVideoSelectorDialog",
            },
        ],
        mount_component_handlers: this.initializeVideoHover.bind(this),
        delete_handlers: this.onDeleteVideo.bind(this),
    };

    setup() {
        this.videoSettingsOverlay = this.dependencies.overlay.createOverlay(VideoSettings, {
            positionOptions: {
                position: "right-start",
            },
            className: "video-overlay",
            closeOnPointerdown: false,
        });
    }

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
        this.dependencies.history.addStep();
    }

    /**
     * Shows the video settings overlay on video block hover.
     * @param {Object} host - The target video block element.
     */
    initializeVideoHover({ host }) {
        const videoBlock = host;

        videoBlock.addEventListener("mouseenter", () => {
            const iframe = videoBlock.querySelector("iframe[title='Video player']");

            this.videoSettingsOverlay.open({
                target: videoBlock,
                props: {
                    overlay: this.videoSettingsOverlay,
                    replaceVideo: () => {
                        this.openVideoSelectorDialog((media) => {
                            this.replaceVideo(media, videoBlock);
                        }, iframe);
                    },
                    removeVideo: () => {
                        videoBlock?.remove();
                        this.videoSettingsOverlay.close();
                        this.dependencies.history.addStep();
                        // After video removal, delay focus to ensure it's inside
                        // the editable when the hint updates, avoiding incorrect
                        // placeholder hints.
                        setTimeout(() => this.dependencies.selection.focusEditable());
                    },
                },
            });

            videoBlock.addEventListener("mouseleave", (e) => {
                if (e.relatedTarget?.closest(".video-overlay")) {
                    return;
                }
                this.videoSettingsOverlay.close();
            });
        });
    }

    /**
     * Replace a video in the editor
     * @param {Object} media
     * @param {Object} videoBlock
     */
    replaceVideo(media, videoBlock) {
        const newVideoBlock = renderToElement("html_editor.EmbeddedVideoBlueprint", {
            embeddedProps: JSON.stringify({
                videoId: media.videoId,
                platform: media.platform,
                params: media.params || {},
            }),
        });
        videoBlock.replaceWith(newVideoBlock);
        this.dependencies.history.addStep();
        this.dependencies.selection.focusEditable();
    }

    onDeleteVideo() {
        if (this.videoSettingsOverlay.isOpen) {
            this.videoSettingsOverlay.close();
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
                ...(iframe && { media: iframe }),
            },
            {
                onClose: () => {
                    restoreSelection();
                },
            }
        );
    }
}
