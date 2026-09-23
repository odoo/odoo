import { describe, expect, mockFetch, test } from "@odoo/hoot";
import { PLATFORMS } from "@html_editor/main/media/media_dialog/video_selector";

for (const [platform, platformClass] of Object.entries(PLATFORMS)) {
    describe(platform, () => {
        for (const [type, url] of Object.entries(platformClass.exampleUrls)) {
            test(`"${type}" URL should be accepted`, async () => {
                mockFetch(() => '{"data": "mockFetch api result data"}');
                const urlMatch = platformClass.isValidVideoUrl(url);
                expect(urlMatch).toBeOfType("object");
                if (!urlMatch) {
                    console.warn(
                        `Fail to parse "${url}".\nThe url "${type}" should be parsable.\nCheck the urlMatcher regex from the ${platform} platform class.`
                    );
                    return;
                }
                const urlData = platformClass.getVideoUrlData(urlMatch); // Ensure the url is parsable (and thus the test valid)
                expect(urlData.platform).toBe(platform);
                const urlToCompare = url.includes("https://") ? url : "https://" + url;
                expect(urlData.baseUrl).toBe(urlToCompare);
                expect(urlData.embedUrl).toBeOfType("string");
                expect(urlData.videoId).toBeOfType("string");
                expect(urlData.videoId).toBe(urlMatch.groups.id || "");
                expect(urlData.options).toBeOfType("object");

                //ensure the embed url is also parsable and match the options of the original url
                const embedUrlMatch = platformClass.isValidVideoUrl(urlData.embedUrl);
                expect(embedUrlMatch).toBeOfType("object");
                if (!embedUrlMatch) {
                    console.warn(
                        `Fail to parse "${urlData.embedUrl}".\nThe embed url given by getVideoUrlData() method should be parsable.`
                    );
                    return;
                }
                const embedUrlData = platformClass.getVideoUrlData(embedUrlMatch);
                expect(embedUrlData.platform).toBe(platform);
                expect(embedUrlData.videoId).toBe(urlData.videoId);
                expect(embedUrlData.options).toEqual(urlData.options);
            });
        }
    });
}

test("a vimeo url keeps its privacy hash and start time", () => {
    mockFetch(() => '{"data": "mockFetch api result data"}');
    for (const [url, embedUrl] of [
        // An unlisted video needs its hash to play.
        [
            "https://vimeo.com/795669787/0763fdb816",
            "https://player.vimeo.com/video/795669787?h=0763fdb816",
        ],
        [
            "https://player.vimeo.com/video/795669787?h=0763fdb816",
            "https://player.vimeo.com/video/795669787?h=0763fdb816",
        ],
        // Vimeo shares the start time in the fragment, in hours, minutes and seconds.
        [
            "https://player.vimeo.com/video/395399735#t=1m2s",
            "https://player.vimeo.com/video/395399735#t=62",
        ],
        [
            "https://player.vimeo.com/video/395399735#t=1h2m3s",
            "https://player.vimeo.com/video/395399735#t=3723",
        ],
        [
            "https://vimeo.com/395399735?autoplay=1#t=62",
            "https://player.vimeo.com/video/395399735?autoplay=1&muted=1#t=62",
        ],
    ]) {
        const urlData = PLATFORMS.vimeo.getVideoUrlData(PLATFORMS.vimeo.isValidVideoUrl(url));
        expect(urlData.embedUrl).toBe(embedUrl);
    }
});

test("playlists are embedded with the right url", () => {
    mockFetch(() => '{"data": "mockFetch api result data"}');
    const list = "playlistId";
    const parent = window.location.hostname;
    for (const [platform, url, embedUrl] of [
        // A playlist has no video: it is embedded through the "videoseries" path.
        [
            "youtube",
            `https://www.youtube.com/playlist?list=${list}`,
            `https://www.youtube.com/embed/videoseries?enablejsapi=1&list=${list}&rel=0`,
        ],
        [
            "youtube",
            `https://www.youtube.com/embed/videoseries?si=AbCdEfGh123&list=${list}`,
            `https://www.youtube.com/embed/videoseries?enablejsapi=1&list=${list}&rel=0`,
        ],
        // A playlist loops on its own: the "playlist" parameter is only used to loop a video.
        [
            "youtube",
            `https://www.youtube.com/playlist?list=${list}&loop=1`,
            `https://www.youtube.com/embed/videoseries?enablejsapi=1&list=${list}&loop=1&rel=0`,
        ],
        // A private or deleted playlist (e.g. "list=WL") would make the video unavailable.
        [
            "youtube",
            "https://www.youtube.com/watch?v=xCvFZrrQq7k&list=WL",
            "https://www.youtube.com/embed/xCvFZrrQq7k?enablejsapi=1&rel=0",
        ],
        ["vimeo", "https://vimeo.com/showcase/1000", "https://vimeo.com/showcase/1000/embed"],
        ["vimeo", "https://vimeo.com/album/1000", "https://vimeo.com/showcase/1000/embed"],
        [
            "dailymotion",
            "https://www.dailymotion.com/playlist/plylist",
            "https://geo.dailymotion.com/player.html?playlist=plylist",
        ],
        // Dailymotion plays the video, then the playlist.
        [
            "dailymotion",
            "https://geo.dailymotion.com/player.html?video=x7svr6t&playlist=plylist",
            "https://geo.dailymotion.com/player.html?video=x7svr6t&playlist=plylist",
        ],
        // The custom player of an embed url is kept.
        [
            "dailymotion",
            "https://geo.dailymotion.com/player/playerId.html?playlist=plylist",
            "https://geo.dailymotion.com/player/playerId.html?playlist=plylist",
        ],
        [
            "twitch",
            "https://www.twitch.tv/collections/collectionId",
            `https://player.twitch.tv/?collection=collectionId&parent=${parent}&muted=true`,
        ],
        // Twitch starts the collection at the given video.
        [
            "twitch",
            "https://www.twitch.tv/videos/1064007405?collection=collectionId",
            `https://player.twitch.tv/?video=1064007405&parent=${parent}&collection=collectionId&muted=true`,
        ],
    ]) {
        const platformClass = PLATFORMS[platform];
        const urlData = platformClass.getVideoUrlData(platformClass.isValidVideoUrl(url));
        expect(urlData.embedUrl).toBe(embedUrl);
    }
});

test("a playlist has no video thumbnail", async () => {
    const fetchedUrls = [];
    mockFetch((input) => {
        fetchedUrls.push(input);
        return '{"thumbnail_url": "https://i.vimeocdn.com/video/showcase"}';
    });
    const getThumbnailUrl = (platform, url) => {
        const platformClass = PLATFORMS[platform];
        return platformClass.getVideoUrlData(platformClass.isValidVideoUrl(url)).thumbnailUrl;
    };
    // A playlist has no video, and thus no video thumbnail.
    expect(getThumbnailUrl("youtube", "https://www.youtube.com/playlist?list=playlistId")).toBe("");
    expect(getThumbnailUrl("dailymotion", "https://www.dailymotion.com/playlist/plylist")).toBe("");
    // Vimeo serves the thumbnail of a showcase through its oembed api.
    expect(await getThumbnailUrl("vimeo", "https://vimeo.com/showcase/1000")).toBe(
        "https://i.vimeocdn.com/video/showcase"
    );
    expect(fetchedUrls).toEqual([
        "https://vimeo.com/api/oembed.json?url=https://vimeo.com/showcase/1000",
    ]);
});

test("options are embedded in the url of each platform", () => {
    mockFetch(() => '{"data": "mockFetch api result data"}');
    const allOptions = { autoplay: true, loop: true, hideControls: true, hideFullscreen: true };
    const parent = window.location.hostname;
    for (const [platform, url, options, embedUrl] of [
        [
            "youtube",
            "https://www.youtube.com/watch?v=xCvFZrrQq7k",
            { ...allOptions, startFrom: 62 },
            "https://www.youtube.com/embed/xCvFZrrQq7k?autoplay=1&enablejsapi=1&controls=0&fs=0&loop=1&mute=1&playlist=xCvFZrrQq7k&rel=0&start=62",
        ],
        [
            "vimeo",
            "https://vimeo.com/395399735",
            { ...allOptions, startFrom: 62 },
            "https://player.vimeo.com/video/395399735?autoplay=1&controls=0&fullscreen=0&loop=1&muted=1#t=62",
        ],
        // A showcase has no start time.
        [
            "vimeo",
            "https://vimeo.com/showcase/1000",
            { ...allOptions, startFrom: 62 },
            "https://vimeo.com/showcase/1000/embed?autoplay=1&controls=0&fullscreen=0&loop=1&muted=1",
        ],
        [
            "dailymotion",
            "https://www.dailymotion.com/video/x7svr6t",
            { startFrom: 62 },
            "https://geo.dailymotion.com/player.html?video=x7svr6t&startTime=62",
        ],
        [
            "facebook",
            "https://www.facebook.com/username/videos/2206239373151307/",
            { autoplay: true, hideFullscreen: true, startFrom: 62 },
            "https://facebook.com/plugins/video.php?href=https%3A%2F%2Fwww.facebook.com%2Fusername%2Fvideos%2F2206239373151307%2F&autoplay=true&allowfullscreen=false&t=62",
        ],
        [
            "twitch",
            "https://www.twitch.tv/videos/1064007405",
            { autoplay: true, startFrom: 62 },
            `https://player.twitch.tv/?video=1064007405&parent=${parent}&muted=true&time=62`,
        ],
        // Twitch autoplays by default: only disabling it is sent.
        [
            "twitch",
            "https://www.twitch.tv/videos/1064007405",
            { autoplay: false },
            `https://player.twitch.tv/?video=1064007405&parent=${parent}&autoplay=false`,
        ],
        [
            "loom",
            "https://www.loom.com/share/e5b8c04bca094dd8a5507925ab887002",
            { autoplay: true, hideControls: true, startFrom: 62 },
            "https://www.loom.com/embed/e5b8c04bca094dd8a5507925ab887002?autoplay=1&hideEmbedTopBar=0&hide_share=0&hide_title=0&hide_owner=0&hide_speed=0&muted=1&t=62",
        ],
    ]) {
        const platformClass = PLATFORMS[platform];
        const urlMatch = platformClass.isValidVideoUrl(url);
        expect(platformClass.getVideoUrlData(urlMatch, options).embedUrl).toBe(embedUrl);
    }
});
