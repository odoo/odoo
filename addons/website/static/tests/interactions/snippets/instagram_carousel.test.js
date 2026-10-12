import { setupInteractionWhiteList, startInteractions } from "@web/../tests/public/helpers";

import { describe, expect, test } from "@odoo/hoot";
import { queryAllAttributes, queryAllTexts } from "@odoo/hoot-dom";

import { onRpc } from "@web/../tests/web_test_helpers";

setupInteractionWhiteList("website.instagram_carousel");

describe.current.tags("interaction_dev");

const template = /* xml */ `
    <section class="s_dynamic_snippet_instagram s_dynamic" data-instagram-account-id="1" data-number-of-records="3" data-number-of-elements="4">
        <div class="dynamic_snippet_template"></div>
    </section>
`;

const feed = {
    username: "odoo",
    profile_picture_url: "https://cdninstagram.com/odoo.jpg",
    posts: [
        {
            media_type: "IMAGE",
            image_url: "https://cdninstagram.com/1.jpg",
            permalink: "https://www.instagram.com/p/1/",
            caption: "Our new collection",
            like_count: 1234,
            comments_count: 0,
        },
        {
            // The likes are hidden by the owner.
            media_type: "VIDEO",
            image_url: "https://cdninstagram.com/2.jpg",
            permalink: "https://www.instagram.com/p/2/",
            caption: "Behind the scenes",
            comments_count: 25300,
        },
        {
            media_type: "CAROUSEL_ALBUM",
            image_url: "https://cdninstagram.com/3.jpg",
            permalink: "https://www.instagram.com/p/3/",
            like_count: 12,
            comments_count: 3,
        },
    ],
};

test("instagram carousel displays the latest posts of its account", async () => {
    onRpc("/website/snippet/instagram_feed", async (request) => {
        const { params } = await request.json();
        expect.step(params);
        return feed;
    });
    await startInteractions(template);
    expect.verifySteps([{ account_id: 1, limit: 3 }]);
    // Images are not loaded in tests: their source is moved to `data-src`.
    expect(queryAllAttributes(".o_instagram_post_header img", "data-src")).toEqual(
        Array(3).fill("https://cdninstagram.com/odoo.jpg")
    );
    expect(queryAllAttributes(".o_instagram_post_header a", "href")).toEqual(
        Array(3).fill("https://www.instagram.com/odoo/")
    );
    expect(queryAllAttributes(".o_instagram_post_media", "href")).toEqual([
        "https://www.instagram.com/p/1/",
        "https://www.instagram.com/p/2/",
        "https://www.instagram.com/p/3/",
    ]);
    expect(queryAllAttributes(".o_instagram_post_media > img", "data-src")).toEqual([
        "https://cdninstagram.com/1.jpg",
        "https://cdninstagram.com/2.jpg",
        "https://cdninstagram.com/3.jpg",
    ]);
    expect(queryAllTexts(".o_instagram_post_caption")).toEqual([
        "odooOur new collection",
        "odooBehind the scenes",
    ]);
});

test("instagram carousel displays the counts like Instagram", async () => {
    onRpc("/website/snippet/instagram_feed", () => feed);
    await startInteractions(template);
    expect(queryAllTexts(".o_instagram_icon_like + .o_instagram_post_metric")).toEqual([
        "1.2K",
        "12",
    ]);
    expect(queryAllTexts(".o_instagram_icon_comment + .o_instagram_post_metric")).toEqual([
        "25.3K",
        "3",
    ]);
});
