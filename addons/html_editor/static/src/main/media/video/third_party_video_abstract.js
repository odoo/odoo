import { rpc } from "@web/core/network/rpc";
import { Plugin } from "@html_editor/plugin";
import { VideoSelector } from "@html_editor/main/media/media_dialog/video_selector";

export class ThirdPartyVideoAbstract extends Plugin {
    static id = "twitch";
    static dependencies = ["history", "dom"];

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
        // To be implemented in child classes
    }

    async insertVideoElement(videoUrl) {
        const videoElement = await this.getVideoElement(videoUrl);
        this.dependencies.dom.insert(videoElement);
        this.dependencies.history.addStep();
    }

    /**
     * @param {string} url
     * @returns {HTMLElement} saved video element or undefined if the URL
     * is not a valid twitch video URL.
     */
    async getVideoElement(url) {
        if (!URL.canParse(url)) {
            return;
        }
        const parsedUrl = new URL(url);
        const urlParams = parsedUrl.searchParams;
        const start_from = urlParams.get("t");

        const videoData = await rpc("/html_editor/video_url/data", {
            video_url: url,
            start_from,
        });
        const savedVideo = this.createVideoElement(videoData);
        savedVideo.classList.add(...VideoSelector.mediaSpecificClasses);
        return savedVideo;
    }

    createVideoElement(videoData) {
        return VideoSelector.createElements([{ src: videoData.embed_url }])[0];
    }
}
