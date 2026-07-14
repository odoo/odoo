import { describe, expect, test } from "@odoo/hoot";
import { contains } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";

describe.current.tags("desktop");
defineWebsiteModels();

test("image link mirrors alignment classes", async () => {
    await setupWebsiteBuilder(
        `<section class="s_test"><div class="d-flex">
            <img class="img img-fluid test-img mx-auto d-block"
                 src="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///ywAAAAAAQABAAACAUwAOw=="/>
        </div></section>`
    );
    await contains(":iframe .test-img").click();
    await contains("[data-action-id='setLink']").click();
    expect(":iframe .d-flex a").toHaveClass("mx-auto");
    await contains("[data-label='Alignment'] .btn-secondary ").click();
    await contains("[data-action-id='imageAndFaAlignClassAction']:contains('Right')").click();
    expect(":iframe .d-flex a").toHaveClass("ms-auto");
    expect(":iframe .d-flex a").not.toHaveClass("mx-auto");
});
