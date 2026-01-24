import { describe, expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilderWithSnippet,
    setupBuilderInteractionWhiteList,
} from "@website/../tests/builder/website_helpers";

describe.current.tags("interaction_dev");

defineWebsiteModels();
setupBuilderInteractionWhiteList(["website.countdown"]);

test("past date: end message is not shown and countdown remains visible", async () => {
    const { interactions } = await setupWebsiteBuilderWithSnippet("s_countdown", {
        enableInteractions: true,
        interactionEditMode: true,
        openEditor: true,
    });

    await interactions.waitReady();
    // Give time for interactions to attach to elements and DOM mutations to settle
    await animationFrame();

    await contains(":iframe .s_countdown").click();
    await contains(".o_customize_tab [data-label='Due Date'] .o-hb-input-base").edit(
        "01/01/2000 00:00"
    );
    // Click away to trigger change
    await contains(".o_customize_tab [data-label='Due Date']").click();
    expect(":iframe .s_countdown_end_message:not(.d-none)").toHaveCount(0);
    expect(":iframe .s_countdown_canvas_flex canvas:not(.d-none)").toHaveCount(4);
});
