import { setSelection } from "@html_editor/../tests/_helpers/selection";
import { describe, expect, test } from "@odoo/hoot";
import {
    advanceTime,
    animationFrame,
    click,
    dblclick,
    manuallyDispatchProgrammaticEvent,
    queryAll,
    queryFirst,
    waitFor,
    waitForNone,
} from "@odoo/hoot-dom";
import { contains, onRpc } from "@web/../tests/web_test_helpers";
import { defineWebsiteModels, setupWebsiteBuilder, dummyBase64Img } from "./website_helpers";
import { testImg } from "./image_test_helpers";
import { delay } from "@web/core/utils/concurrency";
import { expectElementCount } from "@html_editor/../tests/_helpers/ui_expectations";

defineWebsiteModels();

test("click on Image shouldn't open toolbar", async () => {
    const { getEditor } = await setupWebsiteBuilder(
        `<div><p>a</p><img class=a_nice_img src='${dummyBase64Img}'></div>`
    );
    const editor = getEditor();
    const p = editor.editable.querySelector("p");
    setSelection({ anchorNode: p, anchorOffset: 0, focusNode: p, focusOffset: 1 });
    await expectElementCount(".o-we-toolbar", 1);

    await contains(":iframe img.a_nice_img").click();
    await animationFrame();
    await expectElementCount(".o-we-toolbar", 0);
});

test("Double click on image and replace it", async () => {
    onRpc("ir.attachment", "search_read", () => [
        {
            id: 1,
            name: "logo",
            mimetype: "image/png",
            image_src: "/web/static/img/logo2.png",
            access_token: false,
            public: true,
        },
    ]);
    await setupWebsiteBuilder(`<div><img class=a_nice_img src='${dummyBase64Img}'></div>`);
    expect(".modal-content").toHaveCount(0);
    await dblclick(":iframe img.a_nice_img");
    await animationFrame();
    expect(".modal-content:contains(Select a media) .o_upload_media_button").toHaveCount(1);
    expect("div.o-tooltip").toHaveCount(0);
    await contains(".o_select_media_dialog img[title='logo']").click();
    await waitForNone(".o_select_media_dialog");
    expect(":iframe img").toHaveClass("o_modified_image_to_save");
    expect(".options-container[data-container-title='Image']").toHaveCount(1);
});

test("simple click on Image", async () => {
    await setupWebsiteBuilder(`<div><img class=a_nice_img src='${dummyBase64Img}'></div>`);
    await click(":iframe img.a_nice_img");
    await waitFor("div.o-tooltip");
    expect("div.o-tooltip").toHaveCount(1);
    await advanceTime(1600);
    expect("div.o-tooltip").toHaveCount(0);
});

test("double click on text", async () => {
    await setupWebsiteBuilder("<div><p class=text_class>Text</p></div>");
    expect(".modal-content").toHaveCount(0);
    await dblclick(":iframe .text_class");
    await animationFrame();
    expect(".modal-content").toHaveCount(0);
});

test("image should not be draggable", async () => {
    const { getEditor } = await setupWebsiteBuilder(
        `<div><p>a</p><img class=a_nice_img src='${dummyBase64Img}'></div>`
    );
    const editor = getEditor();
    const img = editor.editable.querySelector("img");

    const dragdata = new DataTransfer();
    const events = await manuallyDispatchProgrammaticEvent(img, "dragstart", {
        dataTransfer: dragdata,
    });

    expect(events.get("dragstart").defaultPrevented).toBe(true);
});

describe("Image format/optimize", () => {
    test("Should format an image to be 800px", async () => {
        const { getEditor } = await setupWebsiteBuilder(`
        <div class="test-options-target">
            ${testImg}
        </div>
    `);
        const editor = getEditor();
        await contains(":iframe .test-options-target img").click();

        await contains("[data-label='Format'] .dropdown").click();
        await waitFor('[data-action-id="setImageFormat"]');
        queryAll(`[data-action-id="setImageFormat"]`)
            .find((el) => el.textContent.includes("800px"))
            .click();
        // ensure the shape action has been applied
        await editor.shared.operation.next(() => {});

        const img = queryFirst(":iframe .test-options-target img");
        expect(":iframe .test-options-target img").toHaveAttribute("data-original-id", "1");
        expect(":iframe .test-options-target img").toHaveAttribute("data-mimetype", "image/webp");
        expect(img.src.startsWith("data:image/webp;base64,")).toBe(true);
        await waitFor("[data-label='Format']");
        expect(queryFirst("[data-label='Format'] .dropdown").textContent).toMatch(/800px/);
    });
    test("should set the quality of an image to 50", async () => {
        const { getEditor } = await setupWebsiteBuilder(`
        <div class="test-options-target">
            ${testImg}
        </div>
    `);
        const editor = getEditor();

        const img = await waitFor(":iframe .test-options-target img");
        await contains(":iframe .test-options-target img").click();

        const input = await waitFor('[data-action-id="setImageQuality"] input');
        input.value = 50;
        input.dispatchEvent(new Event("input"));
        await delay();
        input.dispatchEvent(new Event("change"));
        await delay();
        // ensure the shape action has been applied
        await editor.shared.operation.next(() => {});

        expect(img.dataset.quality).toBe("50");
    });
});
