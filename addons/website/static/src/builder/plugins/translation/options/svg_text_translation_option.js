import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { useDomState } from "@html_builder/core/utils";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { getSvgTranslationEls } from "./svg_text_translation_plugin";

export class TranslateSvgTextOption extends BaseOptionComponent {
    static id = "translate_svg_text_option";
    static template = "website.TranslateSvgTextOption";

    setup() {
        super.setup();
        this.state = useDomState((editingElement) => {
            const count = getSvgTranslationEls(editingElement).length;
            return {
                labels: Array.from({ length: count }, (_, index) =>
                    count === 1 ? _t("SVG Text") : _t("SVG Text %s", index + 1)
                ),
            };
        });
    }
}

registry.category("website-options").add(TranslateSvgTextOption.id, TranslateSvgTextOption);
