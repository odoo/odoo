import { patch } from "@web/core/utils/patch";
import { ContentWidthOption } from "@website/builder/plugins/content_width_option_plugin";

patch(ContentWidthOption, {
    exclude: `${ContentWidthOption.exclude}, .s_blog_post_single_circle`,
});
