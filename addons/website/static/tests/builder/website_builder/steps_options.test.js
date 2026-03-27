import { expect, test } from "@odoo/hoot";
import { contains } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilderWithSnippet,
} from "@website/../tests/builder/website_helpers";

defineWebsiteModels();

test("modify the steps color", async () => {
    await setupWebsiteBuilderWithSnippet("s_process_steps");
    await contains(":iframe .s_process_steps").click();
    await contains("[data-label='Connector'] .o_we_color_preview").click();
    await contains(".o-overlay-item [data-color='#FF0000']").click();
    expect(":iframe .s_process_steps .s_process_step path").toHaveStyle({
        stroke: "rgb(255, 0, 0)",
    });
    expect(":iframe marker.s_process_steps_arrow_head path").toHaveStyle({
        fill: "rgb(255, 0, 0)",
    });
});
