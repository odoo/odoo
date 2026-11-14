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
                expect(urlData.videoId).toBe(urlMatch.groups.id);
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

test("vimeo: autoplaying videos disable autopause", async () => {
    mockFetch(() => '{"data": "mockFetch api result data"}');
    const Vimeo = PLATFORMS.vimeo;
    const urlMatch = Vimeo.isValidVideoUrl(Vimeo.exampleUrls.base);
    expect(Vimeo.getVideoUrlData(urlMatch).embedUrl).not.toInclude("autopause");
    // Disabling autopause allows several autoplaying Vimeo videos on a page
    // (e.g. background videos) to play simultaneously.
    const { embedUrl } = Vimeo.getVideoUrlData(urlMatch, { autoplay: true });
    expect(embedUrl).toInclude("autoplay=1");
    expect(embedUrl).toInclude("autopause=0");
    expect(embedUrl).toInclude("muted=1");
});

test("vimeo: the privacy hash of unlisted videos is kept", async () => {
    mockFetch(() => '{"data": "mockFetch api result data"}');
    const Vimeo = PLATFORMS.vimeo;
    const urls = [
        Vimeo.exampleUrls.unlisted,
        Vimeo.exampleUrls.embedUnlisted,
        "https://vimeo.com/795669787/0763fdb816#t=10",
    ];
    for (const url of urls) {
        const { videoId, embedUrl } = Vimeo.getVideoUrlData(Vimeo.isValidVideoUrl(url));
        expect(videoId).toBe("795669787");
        expect(embedUrl).toInclude("player.vimeo.com/video/795669787?");
        expect(new URL(embedUrl).searchParams.get("h")).toBe("0763fdb816");
    }
});

test("vimeo: the start time is kept", async () => {
    mockFetch(() => '{"data": "mockFetch api result data"}');
    const Vimeo = PLATFORMS.vimeo;
    const urls = [
        "https://vimeo.com/395399735#t=62",
        "https://vimeo.com/395399735#t=62s",
        "https://vimeo.com/395399735#t=1m2s",
        "https://player.vimeo.com/video/395399735?autoplay=1&dnt=1#t=62",
    ];
    for (const url of urls) {
        const { options, embedUrl } = Vimeo.getVideoUrlData(Vimeo.isValidVideoUrl(url));
        expect(options.startFrom).toBe(62);
        expect(embedUrl).toMatch(/#t=62$/);
    }
    const unlistedUrl = "https://vimeo.com/795669787/0763fdb816#t=10";
    const { embedUrl } = Vimeo.getVideoUrlData(Vimeo.isValidVideoUrl(unlistedUrl));
    expect(embedUrl).toMatch(/#t=10$/);
});

test("vimeo: do not track is always enabled", async () => {
    mockFetch(() => '{"data": "mockFetch api result data"}');
    const Vimeo = PLATFORMS.vimeo;
    const urlMatch = Vimeo.isValidVideoUrl(Vimeo.exampleUrls.base);
    expect(Vimeo.getVideoUrlData(urlMatch).embedUrl).toInclude("dnt=1");
    expect(Vimeo.getVideoUrlData(urlMatch, { autoplay: true }).embedUrl).toInclude("dnt=1");
});
