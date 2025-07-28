import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { _t } from "@web/core/l10n/translation";

export class ScrollButtonOption extends BaseOptionComponent {
    static template = "website.ScrollButtonOption";
    static selector = "section";
    static exclude =
        "[data-snippet] :not(.oe_structure) > [data-snippet],.s_instagram_page,.o_mega_menu > section,.s_appointments .s_dynamic_snippet_content,.s_floating_blocks,.s_floating_blocks .s_floating_blocks_block";

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
