import { getEmbeddedProps } from "@html_editor/others/embedded_component_utils";
import { Component, signal } from "@odoo/owl";
import { PLATFORMS } from "@html_editor/main/media/media_dialog/video_selector";
import { VideoFile } from "@html_editor/main/media/video/providers/video_file";

export class ReadonlyEmbeddedVideoComponent extends Component {
    static template = "html_editor.EmbeddedVideo";
    static props = {
        // The emebedded video can be initialized either with:
        // the platform and videoId props
        //  OR
        // the src prop
        platform: { type: String, optional: true },
        videoId: { type: String, optional: true },
        src: { type: String, optional: true },
        baseUrl: { type: String, optional: true }, // optional for retro compatibility reason
        params: { type: Object, optional: true },
    };

    playerRef = signal.ref();

    getVideoDataFromSrc(src) {
        for (const platform of Object.values(PLATFORMS)) {
            const urlMatch = platform.isValidVideoUrl(src);
            if (urlMatch) {
                return platform.getVideoUrlData(urlMatch);
            }
        }
        return null;
    }

    /**
     * The description of the video to render, based on the provided props.
     *
     * @returns {Object}
     */
    get videoData() {
        let { platform, videoId, params } = this.props;
        if (!platform || (!videoId && this.props.src)) {
            const videoData = this.getVideoDataFromSrc(this.props.src);
            if (videoData) {
                ({ platform, videoId, options: params } = videoData);
            } else if (this.props.src) {
                platform = VideoFile.id;
            }
        }
        return { platform, videoId, params };
    }

    get isVideoFile() {
        return this.videoData.platform === VideoFile.id;
    }

    /**
     * Get the embed url of the video to render.
     *
     * @returns {string}
     */
    get embedUrl() {
        const { platform, videoId, params } = this.videoData;
        if (platform === VideoFile.id) {
            return VideoFile.getEmbedUrl(this.props.baseUrl || this.props.src, params);
        }
        if (platform && videoId) {
            const platFormClass = PLATFORMS[platform];
            return platFormClass.getEmbedUrl(videoId, params);
        }
        throw new Error("Embeded Video parameters are not valid.");
    }
}

export const readonlyVideoEmbedding = {
    name: "video",
    Component: ReadonlyEmbeddedVideoComponent,
    getProps: (host) => ({ ...getEmbeddedProps(host) }),
};
