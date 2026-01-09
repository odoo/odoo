import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { VideoSelector } from "@html_editor/main/media/media_dialog/video_selector";
import { ThirdPartyVideoAbstract } from "@html_editor/main/media/video/third_party_video_abstract";

export const YOUTUBE_URL_GET_VIDEO_ID =
    /^(?:(?:https?:)?\/\/)?(?:(?:www|m)\.)?(?:youtube\.com|youtu\.be)(?:\/(?:[\w-]+\?v=|embed\/|v\/)?)([^\s?&#]+)(?:\S+)?$/i;

export class YoutubePlugin extends ThirdPartyVideoAbstract {
    static id = "youtube";
    static dependencies = ["history", "dom"];

    mediaSpecificClasses = VideoSelector.mediaSpecificClasses;

    /** @type {import("plugins").EditorResources} */
    resources = {
        ...(this.config.allowVideo && {
            paste_media_url_command_providers: this.getCommandForVideoUrlPaste.bind(this),
        }),
    };

    /**
     * @param {string} url
     */
    getCommandForVideoUrlPaste(url) {
        const youtubeUrl = YOUTUBE_URL_GET_VIDEO_ID.exec(url);
        if (youtubeUrl) {
            // URL is a YouTube video.
            return {
                title: _t("Embed Youtube Video"),
                description: _t("Embed the youtube video in the document."),
                icon: "fa-youtube-play",
                run: () => this.insertVideoElement(youtubeUrl[0]),
            };
        }
    }

    /**
     * @param {string} url
     * @returns {HTMLElement} saved video element or undefined if the URL
     * is not a valid YouTube video URL.
     */
    async getYoutubeVideoElement(url) {
        if (!URL.canParse(url)) {
            return;
        }
        const parsedUrl = new URL(url);
        const urlParams = parsedUrl.searchParams;
        const start_from = urlParams.get("start") || urlParams.get("t");

        const autoplay = urlParams.get("autoplay") === "1";
        const loop = urlParams.get("loop") === "1";
        const hide_controls = urlParams.get("controls") === "0";
        const hide_fullscreen = urlParams.get("fs") === "0";

        const videoData = await rpc("/html_editor/video_url/data", {
            video_url: url,
            autoplay,
            loop,
            hide_controls,
            hide_fullscreen,
            start_from,
        });
        const savedVideo = this.createVideoElement(videoData);
        savedVideo.classList.add(...this.mediaSpecificClasses);
        return savedVideo;
    }
}
