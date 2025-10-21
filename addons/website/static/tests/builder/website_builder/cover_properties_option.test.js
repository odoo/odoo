import { Builder } from "@html_builder/builder";
import { expect, test } from "@odoo/hoot";
import { animationFrame, click, waitFor } from "@odoo/hoot-dom";
import {
    contains,
    dataURItoBlob,
    defineModels,
    models,
    onRpc,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";

defineWebsiteModels();

class BlogPost extends models.Model {
    _name = "blog.post";
}
defineModels([BlogPost]);

const websiteServiceWithUserModelName = {
    async getUserModelName() {
        return "Blog Post";
    },
    // Minimal context to avoid crashes.
    context: {},
    websites: [
        {
            id: 1,
            metadata: {},
        },
    ],
};

test("Add image as cover", async () => {
    patchWithCleanup(Builder.prototype, {
        setup() {
            super.setup();
            this.env.services.website = websiteServiceWithUserModelName;
            this.websiteService = websiteServiceWithUserModelName;
        },
    });

    onRpc("ir.attachment", "search_read", () => [
        {
            id: 1,
            name: "logo",
            mimetype: "image/png",
            image_src: "/web/image/hoot.png",
            access_token: false,
            public: true,
        },
    ]);

    onRpc("/html_editor/get_image_info", () => ({
        attachment: { id: 1 },
        original: { id: 1, image_src: "/web/image/hoot.png", mimetype: "image/png" },
    }));

    onRpc("/web/image/hoot.png", () => {
        const base64Image =
            "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAgAAAAIAQMAAAD+wSzIAAAABlBMVEX///+/v7+jQ3Y5AAAADklEQVQI12P4AIX8EAgALgAD/aNpbtEAAAAASUVORK5CYIIA" +
            "A".repeat(1000); // converted image won't be used if original is not larger
        return dataURItoBlob(base64Image);
    });

    const blogPostTitle = "Title of Test Post";

    await setupWebsiteBuilder(`
        <div class="o_record_cover_container" data-res-model="blog.post" data-res-id="3">
            <div class="o_record_cover_image"/>
            <h1 data-oe-model="blog.post" data-oe-id="3" data-oe-field="name">${blogPostTitle}</h1>
        </div>
    `);

    await contains(":iframe h1").click();
    expect("[data-action-id='setCoverBackground'][data-action-param]").toHaveCount(1);
    await contains("[data-action-id='setCoverBackground'][data-action-param]").click();
    // We use "click" instead of contains.click because contains wait for the image to be visible.
    // In this test we don't want to wait ~800ms for the image to be visible but we can still click on it
    await click(".o_existing_attachment_cell .o_button_area");
    await animationFrame();
    await waitFor(":iframe .o_record_cover_container.o_record_has_cover .o_record_cover_image");
    expect(":iframe .o_record_cover_image").toHaveStyle({
        "background-image": /url\("data:image\/webp;base64,(.*)"\)/,
    });
    expect(":iframe .o_record_cover_image").toHaveClass("o_b64_cover_image_to_save");

    const expectedName = `Blog Post '${blogPostTitle}' cover image.webp`;
    const encodedName = encodeURIComponent(expectedName).replace(/'/g, "%27");
    onRpc("/web_editor/attachment/add_data", async (request) => {
        expect.step("save attachment");
        const { name } = (await request.json()).params;
        expect(name).toBe(expectedName);
        return { image_src: `/web/image/${encodedName}` };
    });
    onRpc("ir.ui.view", "save", ({ args }) => true);
    onRpc("blog.post", "write", ({ args: [[id], { cover_properties }] }) => {
        expect.step("save cover");
        expect(id).toBe(3);
        const { "background-image": bg, resize_class } = JSON.parse(cover_properties);
        expect(bg).toBe(`url("/web/image/${encodedName}")`);
        expect(resize_class.split(" ")).toInclude("o_record_has_cover");
        return true;
    });

    await contains(".o-snippets-top-actions button[data-action='save']").click();
    expect.verifySteps(["save attachment", "save cover"]);
});
