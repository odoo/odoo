import { describe, expect, mockFetch, test } from "@odoo/hoot";
import { TitleDescription } from "@website/components/dialog/seo";

describe.current.tags("headless");

const fillVideoTitles = (seoContext) =>
    TitleDescription.prototype.fillVideoTitles.call({ seoContext });

test("fill empty video descriptions with the video title", async () => {
    mockFetch((input) => {
        expect.step(String(input));
        return { title: "YouTube title" };
    });
    const titleAttributes = [
        { title: "", platform: "youtube", video_id: "Dpq87YCHmJc" },
        { title: "My own description", platform: "youtube", video_id: "W0JQcpGLSFw" },
        { title: "", platform: "facebook", video_id: "123" },
        { title: "" },
    ];
    await fillVideoTitles({ hasDelayedTranslation: false, titleAttributes });
    expect.verifySteps([
        "https://www.youtube.com/oembed?format=json&url=https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3DDpq87YCHmJc",
    ]);
    expect(titleAttributes.map((video) => video.title)).toEqual([
        "YouTube title",
        "My own description",
        "",
        "",
    ]);
    expect(titleAttributes.map((video) => Boolean(video.updated))).toEqual([
        true,
        false,
        false,
        false,
    ]);
});

test("fill nothing when the page has delayed translations", async () => {
    mockFetch(() => expect.step("fetch"));
    const video = { title: "", platform: "youtube", video_id: "Dpq87YCHmJc" };
    await fillVideoTitles({ hasDelayedTranslation: true, titleAttributes: [video] });
    expect.verifySteps([]);
    expect(video.title).toBe("");
});
