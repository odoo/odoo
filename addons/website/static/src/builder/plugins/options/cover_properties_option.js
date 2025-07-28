import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { _t } from "@web/core/l10n/translation";

export class CoverPropertiesOption extends BaseOptionComponent {
    static template = "website.CoverPropertiesOption";
    static selector = ".o_record_cover_container";
    static editableOnly = false;

    setup() {
        super.setup();
        this.state = useDomState((editingElement) => ({
            useTextAlign: editingElement.dataset.use_text_align === "True",
            useSize: editingElement.dataset.use_size === "True",
        }));
        this.coverSizeClasses = Object.keys(coverSizeClassLabels);
    }

    coverSizeLabel(className) {
        return coverSizeClassLabels[className];
    }
}

export const coverSizeClassLabels = {
    o_full_screen_height: _t("Full Screen"),
    o_half_screen_height: _t("Half Screen"),
    cover_auto: _t("Fit text"),
};
