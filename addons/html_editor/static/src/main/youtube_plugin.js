import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { Plugin } from "../plugin";
import { VideoSelector } from "./media/media_dialog/video_selector";

export const YOUTUBE_URL_GET_VIDEO_ID =
    /^(?:(?:https?:)?\/\/)?(?:(?:www|m)\.)?(?:youtube\.com|youtu\.be)(?:\/(?:[\w-]+\?v=|embed\/|v\/)?)([^\s?&#]+)(?:\S+)?$/i;

export class YoutubePlugin extends Plugin {
    static id = "youtube";
    static dependencies = ["history", "powerbox", "link", "dom"];
    resources = {
        paste_url_overrides: this.handlePasteUrl.bind(this),
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
            const restoreSavepoint = this.dependencies.history.makeSavePoint();
            // Open powerbox with commands to embed media or paste as link.
            // Insert URL as text, revert it later if a command is triggered.
            this.dependencies.dom.insert(text);
            this.dependencies.history.addStep();
            // URL is a YouTube video.
            const embedVideoCommand = {
                title: _t("Embed Youtube Video"),
                description: _t("Embed the youtube video in the document."),
                icon: "fa-youtube-play",
                run: async () => {
                    const videoElement = await this.getYoutubeVideoElement(youtubeUrl[0]);
                    this.dependencies.dom.insert(videoElement);
                    this.dependencies.history.addStep();
                },
            };
            const commands = [
                embedVideoCommand,
                this.dependencies.link.getPathAsUrlCommand(text, url),
            ];
            this.dependencies.powerbox.openPowerbox({ commands, onApplyCommand: restoreSavepoint });
            return true;
        }
    }
    // @todo @phoenix: Should this be in this plugin?
    /**
     * @param {string} url
     */
    async getYoutubeVideoElement(url) {
        const parsedUrl = new URL(url);
        const urlParams = parsedUrl.searchParams;
        const autoplay = urlParams.get("autoplay") === "1";
        const loop = urlParams.get("loop") === "1";
        const hide_controls = urlParams.get("controls") === "0";
        const hide_fullscreen = urlParams.get("fs") === "0";
        const { embed_url: src } = await rpc("/html_editor/video_url/data", {
            video_url: url,
            autoplay,
            loop,
            hide_controls,
            hide_fullscreen,
        });
        const [savedVideo] = VideoSelector.createElements([{ src }]);
        savedVideo.classList.add(...VideoSelector.mediaSpecificClasses);
        return savedVideo;
    }
}
