import { getEmbeddedProps } from "@html_editor/others/embedded_component_utils";
import { Component } from "@odoo/owl";
import { PLATFORMS } from "@html_editor/main/media/media_dialog/video_selector";

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
     * Get the embed url for the emebed video based on the provided props.
     * The embed url is computed from the platform and videoId props if they are provided,
     * otherwise it is extracted from the src prop.
     *
     * @returns {string}
     */
    get embedUrl() {
        let platform = this.props.platform;
        let videoId = this.props.videoId;
        let params = this.props.params;
        if (!platform || (!videoId && this.props.src)) {
            const videoData = this.getVideoDataFromSrc(this.props.src);
            if (videoData) {
                platform = videoData.platform;
                videoId = videoData.videoId;
                params = videoData.options;
            }
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
