import { setupHTMLBuilder } from "@html_builder/../tests/helpers";
import { describe, expect, test } from "@odoo/hoot";
import { contains, onRpc } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");

test("image link mirrors alignment classes", async () => {
    onRpc("/html_editor/get_image_info", () => ({}));
    await setupHTMLBuilder(
        `<section class="s_test"><div class="d-flex">
            <img class="img img-fluid test-img mx-auto d-block"
                 src="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///ywAAAAAAQABAAACAUwAOw=="/>
        </div></section>`
    );
    await contains(":iframe .test-img").click();
    await contains("[data-action-id='setLink']").click();
    expect(":iframe .d-flex a").toHaveClass("mx-auto");
    await contains("[data-label='Alignment'] .btn-secondary ").click();
    await contains("[data-action-id='imageAlignClassAction']:contains('Right')").click();
    expect(":iframe .d-flex a").toHaveClass("ms-auto");
    expect(":iframe .d-flex a").not.toHaveClass("mx-auto");
});
