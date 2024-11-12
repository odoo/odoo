import { expect, test } from "@odoo/hoot";
import { animationFrame, dblclick } from "@odoo/hoot-dom";
import { defineWebsiteModels, openSnippetsMenu, setupWebsiteBuilder } from "./helpers";

defineWebsiteModels();

const base64Img =
    "data:image/png;base64, iVBORw0KGgoAAAANSUhEUgAAAAUA\n        AAAFCAYAAACNbyblAAAAHElEQVQI12P4//8/w38GIAXDIBKE0DHxgljNBAAO\n            9TXL0Y4OHwAAAABJRU5ErkJggg==";

test("double click on Image", async () => {
    await setupWebsiteBuilder(`<div><img class=a_nice_img src='${base64Img}'></div>`);
    await openSnippetsMenu();
    expect(".modal-content").toHaveCount(0);
    await dblclick(":iframe img.a_nice_img");
    await animationFrame();
    expect(".modal-content:contains(Select a media) .o_upload_media_button").toHaveCount(1);
});

test("double click on text", async () => {
    await setupWebsiteBuilder("<div><p class=text_class>Text</p></div>");
    await openSnippetsMenu();
    expect(".modal-content").toHaveCount(0);
    await dblclick(":iframe .text_class");
    await animationFrame();
    expect(".modal-content").toHaveCount(0);
});
