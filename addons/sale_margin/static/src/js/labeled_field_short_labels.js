import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { shortLabels } from "@sale/js/labeled_field_short_labels";

patch(shortLabels, {
    getShortLabels() {
        return {
            ...super.getShortLabels(),
            margin: _t("M:"),
            margin_percent: _t("M%:"),
        };
    },
});
