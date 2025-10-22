import {
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";
import { expect, test } from "@odoo/hoot";

defineWebsiteModels();

test("rating snippet should not be user-selectable", async () => {
    await setupWebsiteBuilder(
        `
            <div class="s_rating pt16 pb16" data-icon="fa-star" data-vcss="001" data-snippet="s_rating" data-name="Rating">
                <strong class="s_rating_title">Quality</strong>
                <div class="s_rating_icons o_not_editable">
                    <span class="s_rating_active_icons">
                        <i class="fa fa-star"></i>
                        <i class="fa fa-star"></i>
                        <i class="fa fa-star"></i>
                    </span>
                    <span class="s_rating_inactive_icons">
                        <i class="fa fa-star-o"></i>
                        <i class="fa fa-star-o"></i>
                    </span>
                </div>
            </div>`,
        { loadIframeBundles: true }
    );
    expect(":iframe .s_rating").toHaveStyle({ "user-select": "none" });
});
