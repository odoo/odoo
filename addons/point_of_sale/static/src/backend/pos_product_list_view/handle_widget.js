import { HandleField } from "@web/views/fields/handle/handle_field";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class HandleWidget extends HandleField {
    static template = "web.HandleField";
    static props = {
        ...standardFieldProps,
    };
}

export const handleField = {
    component: HandleWidget,
    displayName: _t("HandleWidget"),
    supportedTypes: ["integer"],
    isEmpty: () => false,
    listViewWidth: 20,
};

registry.category("fields").add("handle_widget", handleField);
