import { AbstractThirdPartyVideo } from "@html_editor/main/media/video/abstract_third_party_video";
import { encodeOptionsToParams } from "@html_editor/main/media/video/utils";

export class Twitch extends AbstractThirdPartyVideo {
    static id = "twitch";
    static name = "Twitch";

    static urlMatcher =
        /^(?:https?:\/\/)?(?:www\.|player\.|clips\.)?twitch\.tv\/(?:(?:(?:videos\/|collections\/|embed\?clip=)|\?(?:([0-9a-z]+)=([0-9a-z_\-.]+)&)*(?:video|collection)=)|[0-9a-z_]{4,25}\/clip\/)(?<id>[0-9a-zA-Z_-]+)(?:[?&=]([0-9a-z_\-.]+))*$/i;

    static optionsConfig = {
        startFrom: { default: 0, type: Number, params: ["time"] },
        autoplay: { default: true, type: Boolean, params: ["autoplay"] },
        muted: { default: false, type: Boolean, params: ["muted"] },
    };

    /**
     * Returns the embed url for a Twitch video, clip or collection.
     *
     * @param {string} videoId
     * @param {Object} options
     * @return {string} url
     */
    static getEmbedUrl(videoId, options = {}) {
        const isClip = options.isClip;
        const isCollection = options.isCollection;
        const params = encodeOptionsToParams(options, Twitch.optionsConfig);
        const parentDomain = window.location.hostname;
        let embedUrl = "";
        if (isClip) {
            embedUrl = `https://clips.twitch.tv/embed?clip=${videoId}&parent=${parentDomain}`;
        } else if (isCollection) {
            // Generates Twitch Collection (Playlist) embed URL: player.twitch.tv/?collection=ID
            embedUrl = `https://player.twitch.tv/?collection=${videoId}&parent=${parentDomain}`;
        } else {
            embedUrl = `https://player.twitch.tv/?video=${videoId}&parent=${parentDomain}`;
        }
        return `${embedUrl}${params ? "&" + params : ""}`;
    }

    /**
     * @override
     * @param {URL} url
     */
    static getCustomUrlOptions(url) {
        return {
            isClip: url.hostname.includes("clip"),
            // Checks if the Twitch URL is a Collection/Playlist (/collections/ in path or ?collection= in query)
            isCollection: url.pathname.includes("/collections/") || url.searchParams.has("collection"),
        };
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
        base: "https://www.twitch.tv/videos/1064007405",
        clip: "https://www.twitch.tv/monstercat/clip/UnrulyShySalamanderPogChamp?filter=clips&range=7d&sort=time",
        collection: "https://www.twitch.tv/collections/cOLlEcTiOnId",
        embed: "https://player.twitch.tv/?video=1064007405&parent=example.com",
        embedClip:
            "https://clips.twitch.tv/embed?clip=UnrulyShySalamanderPogChamp&parent=example.com",
        embedCollection:
            "https://player.twitch.tv/?collection=cOLlEcTiOnId&parent=example.com",
        params: "twitch.tv/videos/1064007405?time=62&autoplay=true&muted=true",
        embedParams:
            "https://player.twitch.tv/?video=1064007405&parent=example.com&time=62&autoplay=true&muted=true",
    };
}
