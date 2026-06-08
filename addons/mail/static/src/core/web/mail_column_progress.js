import { props, t } from "@odoo/owl";

import { ColumnProgress, columnProgressProps } from "@web/views/view_components/column_progress";

export class MailColumnProgress extends ColumnProgress {
    props = props({
        ...columnProgressProps,
        aggregateOn: t.object().optional(),
    });
    static template = "mail.ColumnProgress";
}
