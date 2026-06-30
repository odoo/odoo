import { BaseOptionComponent } from "@html_builder/core/utils";
import { _t } from "@web/core/l10n/translation";

export class BaseAddProductOption extends BaseOptionComponent {
    static template = "html_builder.AddProductOption";
    buttonLabel = _t("Add Product");
}
