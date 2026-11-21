import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";


export function formatX2manyApplication(value) {
    const count = value.currentIds.length;
    if (count === 0) {
        return _t("No Applications");
    } else if (count === 1) {
        return _t("1 Application");
    } else {
        return _t("%s Applications", count);
    }
}

registry
    .category("formatters")
    .add("one2manyApplication", formatX2manyApplication)
    .add("many2manyApplication", formatX2manyApplication)
