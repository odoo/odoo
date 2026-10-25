import { download } from "@web/core/network/download";
import { _t } from "@web/core/l10n/translation";

export const TIME_OFF_EXPORT_FIELDS = [
    { name: "id", label: _t("External ID (update only)") },
    { name: "employee_id", label: _t("Employee") },
    { name: "work_entry_type_id/id", label: _t("Time Type/External ID") },
    { name: "request_date_from", label: _t("Request Start Date") },
    { name: "request_date_to", label: _t("Request End Date") },
];

export function exportTimeOffRecords({ resModel, domain, context }) {
    return download({
        url: "/web/export/xlsx",
        data: {
            data: JSON.stringify({
                import_compat: false,
                context,
                domain,
                fields: TIME_OFF_EXPORT_FIELDS,
                groupby: [],
                ids: false,
                model: resModel,
            }),
        },
    });
}
