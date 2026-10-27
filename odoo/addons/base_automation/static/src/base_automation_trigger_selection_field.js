/** @odoo-module */

import { useState } from "@odoo/owl";
import { _lt, _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useRecordObserver } from "@web/model/relational_model/utils";
import { selectionField, SelectionField } from "@web/views/fields/selection/selection_field";
import { TRIGGER_FILTERS } from "./utils";
import { useService } from "@web/core/utils/hooks";

const OPT_GROUPS = [
    {
        group: { sequence: 10, key: "values", name: _lt("Values Updated") },
        triggers: [
            "on_stage_set",
            "on_user_set",
            "on_tag_set",
            "on_state_set",
            "on_priority_set",
            "on_archive",
            "on_unarchive",
        ],
    },
    {
        group: { sequence: 30, key: "timing", name: _lt("Timing Conditions") },
        triggers: ["on_time", "on_time_created", "on_time_updated"],
    },
    {
        group: { sequence: 40, key: "custom", name: _lt("Custom") },
        triggers: ["on_create_or_write", "on_unlink", "on_change"],
    },
    {
        group: { sequence: 50, key: "external", name: _lt("External") },
        triggers: ["on_webhook"],
    },
    {
        group: { sequence: 20, key: "mail", name: _t("Email Events") },
        triggers: ["on_message_sent", "on_message_received"],
    },
    {
        group: { sequence: 60, key: "deprecated", name: _lt("Deprecated (do not use)") },
        triggers: ["on_create", "on_write"],
    },
];

function computeDerivedOptions(options, fields, currentSelection, { excludeGroups = [] } = {}) {
    // filter options to display, derived from the current value and the model fields
    const derivedOptions = [];
    for (const [value, label] of options) {
        const { group, triggers } = OPT_GROUPS.find((g) => g.triggers.includes(value));
        if (
            (group.key === "deprecated" && !triggers.includes(currentSelection)) ||
            excludeGroups.includes(group.key)
        ) {
            // skip deprecated triggers if the current value is not deprecated
            continue;
        }
        const filterFn = TRIGGER_FILTERS[value];
        if (filterFn) {
            const triggerFields = fields.filter(filterFn);
            if (triggerFields.length === 0) {
                // skip triggers that don't have any corresponding field
                continue;
            }
        }

        const option = { group, value, label };
        derivedOptions.push(option);
    }
    return derivedOptions;
}

export class TriggerSelectionField extends SelectionField {
    static template = "base_automation.TriggerSelectionField";
    setup() {
        super.setup();
        this.groupedOptions = useState([]);

        const orm = useService("orm");
        let lastRelatedModelId;
        let relatedModelFields;
        useRecordObserver(async (record) => {
            const { data, fields } = record;
            const modelId = data.model_id?.[0];
            if (lastRelatedModelId !== modelId) {
                lastRelatedModelId = modelId;
                relatedModelFields = await orm.searchRead(
                    "ir.model.fields",
                    [["model_id", "=", modelId]],
                    ["field_description", "name", "ttype", "relation"]
                );
            }

            // first, compute the derived options
            const derivedOptions = computeDerivedOptions(
                fields[this.props.name].selection,
                relatedModelFields,
                data[this.props.name],
                { excludeGroups: data.model_is_mail_thread ? [] : ["mail"] }
            );

            // then group and sort them
            this.groupedOptions.length = 0;
            for (const option of derivedOptions) {
                const group = this.groupedOptions.find((g) => g.key === option.group.key) ?? {
                    ...option.group,
                    options: [],
                };
                group.options.push(option);
                if (!this.groupedOptions.includes(group)) {
                    this.groupedOptions.push(group);
                }
            }
            this.groupedOptions.sort((a, b) => a.sequence - b.sequence);
        });
    }
}

export const triggerSelectionField = {
    ...selectionField,
    component: TriggerSelectionField,
    fieldDependencies: [{ name: "model_is_mail_thread", type: "boolean" }],
};
registry.category("fields").add("base_automation_trigger_selection", triggerSelectionField);
