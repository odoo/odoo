import { setSelection } from "@html_editor/../tests/_helpers/selection";
import { expect, test } from "@odoo/hoot";
import { animationFrame, dblclick, waitFor } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";
import { defineWebsiteModels, setupWebsiteBuilder, dummyBase64Img } from "./website_helpers";

defineWebsiteModels();

test("click on Image shouldn't open toolbar", async () => {
    const { getEditor } = await setupWebsiteBuilder(
        `<div><p>a</p><img class=a_nice_img src='${dummyBase64Img}'></div>`
    );
    const editor = getEditor();
    const p = editor.editable.querySelector("p");
    setSelection({ anchorNode: p, anchorOffset: 0, focusNode: p, focusOffset: 1 });
    await waitFor(".o-we-toolbar");
    expect(".o-we-toolbar").toHaveCount(1);

    await contains(":iframe img.a_nice_img").click();
    await animationFrame();
    expect(".o-we-toolbar").toHaveCount(0);
});

test("double click on Image", async () => {
    await setupWebsiteBuilder(`<div><img class=a_nice_img src='${dummyBase64Img}'></div>`);
    expect(".modal-content").toHaveCount(0);
    await dblclick(":iframe img.a_nice_img");
    await animationFrame();
    expect(".modal-content:contains(Select a media) .o_upload_media_button").toHaveCount(1);
});

test("double click on text", async () => {
    await setupWebsiteBuilder("<div><p class=text_class>Text</p></div>");
    expect(".modal-content").toHaveCount(0);
    await dblclick(":iframe .text_class");
    await animationFrame();
    expect(".modal-content").toHaveCount(0);
});
