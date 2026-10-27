import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { CharField, charField } from "@web/views/fields/char/char_field";

/**
 * Char field showing its full value as a tooltip when it overflows the input.
 */
export class CharOverflowTitleField extends CharField {
    static template = "web.CharOverflowTitleField";

    onMouseEnter(ev) {
        const input = ev.currentTarget;
        input.title = input.scrollWidth > input.clientWidth ? input.value : "";
    }
}

export const charOverflowTitleField = {
    ...charField,
    component: CharOverflowTitleField,
    displayName: _t("Text (full value on hover)"),
};

registry.category("fields").add("char_overflow_title", charOverflowTitleField);
