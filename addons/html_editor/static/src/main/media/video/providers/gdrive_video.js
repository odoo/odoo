import { AbstractThirdPartyVideo } from "@html_editor/main/media/video/abstract_third_party_video";

export class GDriveVideo extends AbstractThirdPartyVideo {
    static id = "gDrive";
    static name = "Google Drive";

    static urlMatcher =
        /^https:\/\/drive\.google\.com\/file\/d\/(?<id>.*?)\/.*?(?:\?[0-9a-z_\-=&]+)?$/i;

    /**
     * Returns the embed url for a Google Drive video.
     *
     * @param {string} videoId
     * @param {Object} options
     * @return {string} url
     */
    static getEmbedUrl(videoId, options = {}) {
        return `https://drive.google.com/file/d/${videoId}/preview`;
    }
}
