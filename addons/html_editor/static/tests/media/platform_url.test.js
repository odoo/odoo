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
