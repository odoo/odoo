import { expect, test, beforeEach } from "@odoo/hoot";
import { queryAllTexts, queryAllValues, waitFor } from "@odoo/hoot-dom";
import { xml } from "@odoo/owl";
import { contains, mockService } from "@web/../tests/web_test_helpers";
import { addBuilderOption, setupHTMLBuilder, addBuilderPlugin } from "./helpers";
import { ShadowOptionPlugin } from "@html_builder/plugins/shadow_option_plugin";

beforeEach(() => {
    mockService("website", () => ({
        currentWebsite: {
            id: 1,
            metadata: {
                lang: "en_US",
            },
            default_lang_id: {
                code: "en_US",
            },
        },
    }));
});

test("edit box-shadow with ShadowOption", async () => {
    addBuilderOption({
        selector: ".test-options-target",
        template: xml`<ShadowOption/>`,
    });
    addBuilderPlugin(ShadowOptionPlugin);
    await setupHTMLBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();
    await waitFor(".hb-row");
    expect(queryAllTexts(".hb-row .hb-row-label")).toEqual(["Shadow"]);
    expect(":iframe .test-options-target").toHaveOuterHTML(
        '<div class="test-options-target o-paragraph">b</div>'
    );

    await contains('.options-container button[title="Outset"]').click();
    expect(queryAllTexts(".hb-row .hb-row-label")).toEqual([
        "Shadow",
        "Color",
        "Offset (X, Y)",
        "Blur",
        "Spread",
    ]);
    expect(queryAllValues('[data-action-id="setShadow"] input')).toEqual(["0", "8", "16", "0"]);
    expect(":iframe .test-options-target").toHaveOuterHTML(
        '<div class="test-options-target o-paragraph shadow" style="box-shadow: rgba(0, 0, 0, 0.15) 0px 8px 16px 0px !important;">b</div>'
    );

    await contains('[data-action-param="offsetX"] input').fill(10);
    await contains('[data-action-param="offsetY"] input').fill(2, { clean: true });
    expect(":iframe .test-options-target").toHaveOuterHTML(
        '<div class="test-options-target o-paragraph shadow" style="box-shadow: rgba(0, 0, 0, 0.15) 10px 82px 16px 0px !important;">b</div>'
    );

    await contains('[data-action-param="blur"] input').fill(3);
    expect(":iframe .test-options-target").toHaveOuterHTML(
        '<div class="test-options-target o-paragraph shadow" style="box-shadow: rgba(0, 0, 0, 0.15) 10px 82px 163px 0px !important;">b</div>'
    );

    await contains('[data-action-param="spread"] input').fill(4);
    expect(":iframe .test-options-target").toHaveOuterHTML(
        '<div class="test-options-target o-paragraph shadow" style="box-shadow: rgba(0, 0, 0, 0.15) 10px 82px 163px 4px !important;">b</div>'
    );

    await contains('.options-container button[title="Inset"]').click();
    expect(queryAllTexts(".hb-row .hb-row-label")).toEqual([
        "Shadow",
        "Color",
        "Offset (X, Y)",
        "Blur",
        "Spread",
    ]);
    expect(queryAllValues('[data-action-id="setShadow"] input')).toEqual(["10", "82", "163", "4"]);
    expect(":iframe .test-options-target").toHaveOuterHTML(
        '<div class="test-options-target o-paragraph shadow" style="box-shadow: rgba(0, 0, 0, 0.15) 10px 82px 163px 4px inset !important;">b</div>'
    );

    await contains(".options-container button:contains(None)").click();
    expect(queryAllTexts(".hb-row .hb-row-label")).toEqual(["Shadow"]);
    expect(":iframe .test-options-target").toHaveOuterHTML(
        '<div class="test-options-target o-paragraph" style="">b</div>'
    );
});
