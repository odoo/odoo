import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

export class ScrollButtonOption extends BaseOptionComponent {
    static id = "scroll_button_option";
    static template = "website.ScrollButtonOption";

    setup() {
        super.setup();
        this.state = useDomState((editingElement) => ({
            heightLabel:
                editingElement.dataset.snippet === "s_image_gallery"
                    ? _t("Min-Height")
                    : _t("Height"),
            heightFieldEnabled: editingElement.dataset.snippet === "s_image_gallery",
            scrollDownButtonDisabled: editingElement.matches("footer section"),
        }));
    }

    showHeightField() {
        return this.state.heightFieldEnabled && this.isActiveItem("minheight_auto_opt");
    }
}
registry.category("website-options").add(ScrollButtonOption.id, ScrollButtonOption);
