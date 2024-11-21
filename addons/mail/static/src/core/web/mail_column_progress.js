import { ColumnProgress } from "@web/views/view_components/column_progress";

export class MailColumnProgress extends ColumnProgress {
    static props = {
        ...ColumnProgress.props,
        aggregateOn: { type: Object, optional: true },
    };
    static template = "mail.ColumnProgress";
}
