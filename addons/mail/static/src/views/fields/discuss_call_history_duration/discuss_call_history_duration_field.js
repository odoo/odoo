import { Component, useProps } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { formatDuration } from "@web/views/fields/formatters";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class DiscussCallHistoryDurationField extends Component {
    static template = "mail.DiscussCallHistoryDurationField";

    props = useProps(standardFieldProps);

    get formattedValue() {
        return formatDuration(
            { seconds: this.props.record.data[this.props.name] * 3600 },
            { showSeconds: true, unit: "seconds" }
        );
    }
}

export const discussCallHistoryDurationField = {
    component: DiscussCallHistoryDurationField,
    displayName: _t("Call Duration"),
    supportedTypes: ["float"],
};

registry.category("fields").add("discuss_call_history_duration", discussCallHistoryDurationField);
