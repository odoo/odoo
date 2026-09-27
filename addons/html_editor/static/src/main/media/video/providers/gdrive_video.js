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

    /**
     * Example urls are used to test that the urlMatcher regular expression
     * correctly identifies valid video urls and extracts the video ID.
     * Every urls in this object should be parsable by the urlMatcher.
     *
     * The `base` Url is also used in media dialog unit tests.
     *
     * @see /addons/html_editor/static/tests/media/*.test.js
     * */
    static exampleUrls = {
        base: "https://drive.google.com/file/d/1A2B3C4D5E6F7G8H9I0J/view?usp=sharing",
        embed: "drive.google.com/file/d/1A2B3C4D5E6F7G8H9I0J/preview",
    };
}
