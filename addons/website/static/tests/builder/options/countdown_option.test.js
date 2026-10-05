import { expect, test } from "@odoo/hoot";
import { queryFirst, waitFor } from "@odoo/hoot-dom";
import { contains, getService } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilderWithSnippet,
} from "@website/../tests/builder/website_helpers";

defineWebsiteModels();

async function setLayout(layout, selectorAdd = "") {
    await waitFor("[data-label='At The End']");
    await contains("[data-label='At The End'] button.o-dropdown").click();
    await contains(`.popover [data-action-value='${layout}']`).click();
    expect(`:iframe .s_countdown${selectorAdd}`).toHaveAttribute("data-end-action", layout);
}

test("hide countdown when end action is set to message_no_countdown", async () => {
    await setupWebsiteBuilderWithSnippet("s_countdown", { loadIframeBuilderTemplates: true });
    await contains(":iframe .s_countdown").click();
    expect(":iframe .s_countdown").toHaveAttribute("data-end-action", "nothing");
    expect(":iframe .s_countdown").not.toHaveClass("hide-countdown");

    await setLayout("message_no_countdown");
    expect(":iframe .s_countdown").toHaveClass("hide-countdown");

    await setLayout("message");
    expect(":iframe .s_countdown").not.toHaveClass("hide-countdown");
});

test("save end message when switching layouts, forget when switching snippets", async () => {
    await setupWebsiteBuilderWithSnippet(["s_countdown", "s_countdown"], {
        loadIframeBuilderTemplates: true,
    });
    await contains(":iframe .s_countdown:first-child").click();

    await setLayout("message", ":first-child");

    const endMessageEl = queryFirst(":iframe .s_countdown .s_countdown_end_message");
    endMessageEl.innerHTML = "test";

    await setLayout("nothing", ":first-child");
    await setLayout("message", ":first-child");

    expect(":iframe .s_countdown .s_countdown_end_message").toHaveInnerHTML("test");

    await contains(":iframe .s_countdown:nth-child(2)").click();
    await setLayout("message", ":nth-child(2)");
    expect(":iframe .s_countdown:nth-child(2) .s_countdown_end_message").not.toHaveInnerHTML(
        "test"
    );
});

test("cloned countdown starts its interaction", async () => {
    await setupWebsiteBuilderWithSnippet("s_countdown", { interactions: ["website.countdown"] });
    await contains(":iframe .s_countdown").click();
    await contains(".oe_snippet_clone").click();
    await waitFor(":iframe .s_countdown:eq(1) canvas");
    expect(getService("public.interactions").interactions).toHaveLength(2);
    expect(queryFirst(":iframe .s_countdown:eq(1) canvas")
        .getContext("2d")
        .getImageData(0, 0, 1000, 1000)
        .data).toInclude(1, {
            message: "The cloned snippet should have been started"
        });
});
