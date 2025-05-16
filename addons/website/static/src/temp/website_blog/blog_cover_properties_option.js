import { patch } from "@web/core/utils/patch";
import { useDomState } from "@html_builder/core/utils";
import { CoverPropertiesOption } from "@website/website_builder/plugins/options/cover_properties_option";

patch(CoverPropertiesOption, {
    template: "website_blog.BlogCoverPropertiesOption",
});
patch(CoverPropertiesOption.prototype, {
    setup() {
        super.setup();
        this.blogState = useDomState((editingElement) => ({
            isRegularCover: editingElement.classList.contains("o_wblog_post_page_cover_regular"),
        }));
    },
});
