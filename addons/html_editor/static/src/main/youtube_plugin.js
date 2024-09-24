import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { Plugin } from "../plugin";
import { VideoSelector } from "./media/media_dialog/video_selector";

export const YOUTUBE_URL_GET_VIDEO_ID =
    /^(?:(?:https?:)?\/\/)?(?:(?:www|m)\.)?(?:youtube\.com|youtu\.be)(?:\/(?:[\w-]+\?v=|embed\/|v\/)?)([^\s?&#]+)(?:\S+)?$/i;

export class YoutubePlugin extends Plugin {
    static name = "youtube";
    static dependencies = ["history", "powerbox", "link", "dom"];
    static shared = [];
    resources = {
        handle_paste_url: this.handlePasteUrl.bind(this),
    };
    /**
     * @param {string} text
     * @param {string} url
     */
    handlePasteUrl(text, url) {
        // to know if this logic should be executed or not. Do we still want an
        // option of do we want to add a plugin whenever we want the feature?
        const youtubeUrl = !this.config.disableVideo && YOUTUBE_URL_GET_VIDEO_ID.exec(url);
        if (youtubeUrl) {
            const restoreSavepoint = this.shared.makeSavePoint();
            // Open powerbox with commands to embed media or paste as link.
            // Insert URL as text, revert it later if a command is triggered.
            this.shared.domInsert(text);
            this.dispatch("ADD_STEP");
            // URL is a YouTube video.
            const embedVideoCommand = {
                name: _t("Embed Youtube Video"),
                description: _t("Embed the youtube video in the document."),
                fontawesome: "fa-youtube-play",
                action: async () => {
                    const videoElement = await this.getYoutubeVideoElement(youtubeUrl[0]);
                    this.shared.domInsert(videoElement);
                    this.dispatch("ADD_STEP");
                },
            };
            const commands = [embedVideoCommand, this.shared.getPathAsUrlCommand(text, url)];
            this.shared.openPowerbox({ commands, onApplyCommand: restoreSavepoint });
            return true;
        }
    }
    // @todo @phoenix: Should this be in this plugin?
    /**
     * @param {string} url
     */
    async getYoutubeVideoElement(url) {
        const { embed_url: src } = await rpc("/html_editor/video_url/data", {
            video_url: url,
        });
        const [savedVideo] = VideoSelector.createElements([{ src }]);
        savedVideo.classList.add(...VideoSelector.mediaSpecificClasses);
        return savedVideo;
    }
}
