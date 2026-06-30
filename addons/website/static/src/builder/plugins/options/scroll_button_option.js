import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { _t } from "@web/core/l10n/translation";

export class ScrollButtonOption extends BaseOptionComponent {
    static template = "website.ScrollButtonOption";
    static selector = "section";
    static exclude =
        "[data-snippet] :not(.oe_structure) > [data-snippet], .s_instagram_page, .o_mega_menu > section, .s_appointments .s_dynamic_snippet_content, .s_bento_banner section[data-name='Card'], .s_floating_blocks, .s_floating_blocks .s_floating_blocks_block, .s_bento_block_card, .s_dynamic_category, .s_dynamic_category .s_dynamic_snippet_title, .s_announcement_scroll";

    setup() {
        super.setup();
        this.state = useDomState((editingElement) => ({
            heightLabel:
                editingElement.dataset.snippet === "s_image_gallery"
                    ? _t("Min-Height")
                    : _t("Height"),
            heightFieldEnabled: editingElement.dataset.snippet === "s_image_gallery",
        }));
    }

    showHeightField() {
        return this.state.heightFieldEnabled && this.isActiveItem("minheight_auto_opt");
    }
}
