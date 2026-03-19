import { expect, test } from "@odoo/hoot";
import { click, dblclick } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import {
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";

defineWebsiteModels();

test("Icon styles should be retained when it is replaced with another icon", async () => {
    const extractClasses = "rounded-circle rounded shadow img-thumbnail";
    await setupWebsiteBuilder(`<i class="oi ${extractClasses}" data-icon="search"/>`);

    await dblclick(":iframe .oi");
    await animationFrame();
    await click("[data-icon=favorite]");
    await animationFrame();
    expect(":iframe [data-icon=favorite]").toHaveClass(extractClasses);
});
