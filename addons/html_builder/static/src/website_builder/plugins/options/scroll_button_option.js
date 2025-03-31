import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { _t } from "@web/core/l10n/translation";

export class ScrollButtonOption extends BaseOptionComponent {
    static template = "html_builder.ScrollButtonOption";
    static props = {};

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
        return this.state.heightFieldEnabled && this.isActiveItem("fit_content_opt");
    }
}
