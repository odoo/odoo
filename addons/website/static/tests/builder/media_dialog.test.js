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
    await setupWebsiteBuilder(`<i class="fa fa-search ${extractClasses}"/>`);

    await dblclick(":iframe .fa");
    await animationFrame();
    await click(".fa-heart");
    expect(":iframe .fa-heart").toHaveClass(extractClasses);
});
