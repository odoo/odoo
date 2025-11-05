import { Component, useProps } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class DiscussCallHistoryIndicatorsField extends Component {
    static template = "mail.DiscussCallHistoryIndicatorsField";

    props = useProps(standardFieldProps);

    get icons() {
        if (this.props.record.data.has_video) {
            return [{ label: _t("Video recording"), name: "movie" }];
        }
        if (this.props.record.data.has_audio) {
            return [{ label: _t("Audio recording"), name: "volume_up" }];
        }
        return [];
    }
}

export const discussCallHistoryIndicatorsField = {
    component: DiscussCallHistoryIndicatorsField,
    displayName: _t("Call Recording Indicators"),
    fieldDependencies: [
        { name: "has_audio", type: "boolean" },
        { name: "has_video", type: "boolean" },
    ],
    supportedTypes: ["boolean"],
};

registry
    .category("fields")
    .add("discuss_call_history_indicators", discussCallHistoryIndicatorsField);
