import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import {
    listBadgeSelectionField,
    ListBadgeSelectionField,
} from "@web/views/fields/badge_selection/list_badge_selection_field";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export function getRottingDaysTitle(modelName, rotDays) {
    switch (modelName) {
        case "crm.lead":
            return _t("This lead has been stuck in this stage for %(numberOfDays)s days.", {
                numberOfDays: rotDays,
            });
        case "hr.applicant":
            return _t("This applicant has been stuck in this stage for %(numberOfDays)s days.", {
                numberOfDays: rotDays,
            });
        case "project.task":
            return _t("This task has been stuck in this stage for %(numberOfDays)s days.", {
                numberOfDays: rotDays,
            });
    }
    return _t("This record has been stuck in this stage for %(numberOfDays)s days.", {
        numberOfDays: rotDays,
    });
}

export class KanbanRottingField extends Component {
    static props = {
        ...standardFieldProps,
    };
    static template = "mail.KanbanRottingField";

    setup() {
        // Preprocess all sentences as childless strings so they're easier to format in the DOM
        this.dayCount = _t("%(numberOfDays)sd", {
            numberOfDays: this.props.record.data.rotting_days,
        });

        this.title = getRottingDaysTitle(
            this.props.record.model.config.resModel,
            this.props.record.data.rotting_days
        );
    }
}

export class ListBadgeSelectionRotting extends ListBadgeSelectionField {
    static template = "mail.ListBadgeSelectionRotting";
    setup() {
        super.setup();
        // As this widget is appended to another field's value, we display no additional title to prevent title overlap
        this.dayCount = _t("%(numberOfDays)sd", {
            numberOfDays: this.props.record.data.rotting_days,
        });
    }
}

registry.category("fields").add("kanban.rotting", {
    component: KanbanRottingField,
});

registry.category("fields").add("list.badge_rotting", {
    ...listBadgeSelectionField,
    component: ListBadgeSelectionRotting,
});
