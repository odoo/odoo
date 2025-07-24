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
    queryOne,
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
    await contains(".o_select_media_dialog .o_button_area[aria-label='logo']").click();
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

function pasteFile(editor, file) {
    const clipboardData = new DataTransfer();
    clipboardData.items.add(file);
    const pasteEvent = new ClipboardEvent("paste", { clipboardData, bubbles: true });
    editor.editable.dispatchEvent(pasteEvent);
}

function createBase64ImageFile(base64ImageData, filename) {
    const binaryImageData = atob(base64ImageData);
    const uint8Array = new Uint8Array(binaryImageData.length);
    for (let i = 0; i < binaryImageData.length; i++) {
        uint8Array[i] = binaryImageData.charCodeAt(i);
    }
    return new File([uint8Array], filename ?? "test_image.png", { type: "image/png" });
}

test("pasted/dropped images are converted to attachments on save in website editor", async () => {
    onRpc("/html_editor/attachment/add_data", async (request) => {
        const { params } = await request.json();
        expect(
            params.data ===
                "iVBORw0KGgoAAAANSUhEUgAAAAgAAAAIAQMAAAD+wSzIAAAABlBMVEX///+/v7+jQ3Y5AAAADklEQVQI12P4AIX8EAgALgAD/aNpbtEAAAAASUVORK5CYII="
        ).toBe(true);
        expect.step("add_data");
        return {
            image_src: "/test_image_url.png",
            access_token: "1234",
            public: false,
        };
    });

    onRpc("ir.ui.view", "save", ({ args }) => {
        expect.step("save");
        expect(args[1]).toInclude('src="/test_image_url.png?access_token=1234"');
        return true;
    });

    const { getEditor } = await setupWebsiteBuilder(`
        <section>
            <p>Text</p>
            <p><br></p>
            <p>More Text</p>
        </section>
    `);

    const editor = getEditor();

    // Paste image
    var p = queryOne(":iframe section > p:has(br)");
    setSelection({ anchorNode: p, anchorOffset: 0 });
    pasteFile(
        editor,
        createBase64ImageFile(
            "iVBORw0KGgoAAAANSUhEUgAAAAgAAAAIAQMAAAD+wSzIAAAABlBMVEX///+/v7+jQ3Y5AAAADklEQVQI12P4AIX8EAgALgAD/aNpbtEAAAAASUVORK5CYII"
        )
    );

    // Check if image is set to be saved as attachment
    await waitFor(":iframe img.o_b64_image_to_save");
    expect(
        queryOne(":iframe img.o_b64_image_to_save").src.startsWith("data:image/png;base64,")
    ).toBe(true);

    // Save and check if image has been saved as attachment
    await contains(".o-snippets-top-actions button:contains(Save)").click();
    expect.verifySteps(["add_data", "save"]);
});

test("pasted/dropped images are converted to attachments on snippet save", async () => {
    const imageData =
        "iVBORw0KGgoAAAANSUhEUgAAAAgAAAAIAQMAAAD+wSzIAAAABlBMVEX///+/v7+jQ3Y5AAAADklEQVQI12P4AIX8EAgALgAD/aNpbtEAAAAASUVORK5CYII";
    onRpc("/html_editor/attachment/add_data", async (request) => {
        const { params } = await request.json();
        expect(params.data).toBe(imageData + "=");
        expect.step(`add_data ${params.name}`);
        return {
            image_src: `/url_${params.name}`,
            access_token: "1234",
            public: false,
        };
    });

    onRpc("ir.ui.view", "save_snippet", ({ kwargs }) => {
        expect.step("save snippet");
        expect(kwargs.arch).toInclude('src="/url_image-1.png?access_token=1234"');
        return "Custom Cover";
    });

    onRpc("ir.ui.view", "save", ({ args }) => {
        expect.step("save");
        expect(args[1]).toInclude('src="/url_image-1.png?access_token=1234"');
        expect(args[1]).toInclude('src="/url_image-2.png?access_token=1234"');
        return true;
    });

    const { getEditor } = await setupWebsiteBuilder(`
        <section data-snippet="s_cover" test-id="1">
            <p>Text</p>
            <p><br></p>
            <p>More Text</p>
        </section>
        <section data-snippet="s_cover" test-id="2">
            <p>Text</p>
            <p><br></p>
            <p>More Text</p>
        </section>
    `);

    const editor = getEditor();

    // Paste images
    let p = queryOne(":iframe section[test-id='1'] > p:has(br)");
    setSelection({ anchorNode: p, anchorOffset: 0 });
    pasteFile(editor, createBase64ImageFile(imageData, "image-1.png"));

    // Check if image is set to be saved as attachment
    expect(await waitFor(":iframe [test-id='1'] img.o_b64_image_to_save")).toHaveAttribute(
        "src",
        /^data:image\/png;base64,/
    );

    p = queryOne(":iframe section[test-id='2'] > p:has(br)");
    setSelection({ anchorNode: p, anchorOffset: 0 });
    pasteFile(editor, createBase64ImageFile(imageData, "image-2.png"));

    // Check if image is set to be saved as attachment
    expect(await waitFor(":iframe [test-id='2'] img.o_b64_image_to_save")).toHaveAttribute(
        "src",
        /^data:image\/png;base64,/
    );

    // Save snippet of section 1 and check if its image has been saved as attachment
    await contains(":iframe [test-id='1']").click();
    await contains("button.oe_snippet_save").click();
    await contains(".modal button:contains(Save)").click();
    await expect.waitForSteps(["add_data image-1.png", "save snippet"]);

    // Save and check if image of section 2 has been saved as attachment
    await contains(".o-snippets-top-actions button:contains(Save)").click();
    await expect.waitForSteps(["add_data image-2.png", "save"]);
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
        expect(":iframe .test-options-target img").toHaveAttribute("data-attachment-id", "1");
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
