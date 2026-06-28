import { t } from "@odoo/owl";

export const standardWidgetProps = {
    readonly: t.boolean().optional(),
    record: t.object(),
};
