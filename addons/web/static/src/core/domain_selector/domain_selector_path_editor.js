/** @odoo-module **/

import { formatValue } from "@web/core/domain_tree";
import { _t } from "@web/core/l10n/translation";
import { ModelFieldSelector } from "@web/core/model_field_selector/model_field_selector";

export function getPathEditorInfo(params) {
    return {
        component: ModelFieldSelector,
        extractProps: ({ update, value: path }) => {
            const { resModel, isDebugMode } = params;
            return {
                path,
                update,
                resModel,
                isDebugMode,
                readonly: false,
            };
        },
        isSupported: (path) => [0, 1].includes(path) || typeof path === "string",
        defaultValue: () => params.defaultPath,
        stringify: (path) => formatValue(path),
        message: _t("Invalid field chain"),
    };
}
