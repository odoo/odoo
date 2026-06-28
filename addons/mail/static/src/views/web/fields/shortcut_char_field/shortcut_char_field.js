import { Component, props } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { CharField, charFieldProps } from "@web/views/fields/char/char_field";

export class ShortcutCharField extends Component {
    static template = "mail.ShortcutCharField";
    static components = { CharField };
    props = props({ ...charFieldProps });

    get charProps() {
        return {
            ...this.props,
            placeholder: _t("e.g. hello"),
        };
    }
}

registry.category("fields").add("shortcut", {
    component: ShortcutCharField,
});
