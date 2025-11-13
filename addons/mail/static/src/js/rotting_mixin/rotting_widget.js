import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { buildM2OFieldDescription, Many2OneField } from "@web/views/fields/many2one/many2one_field";
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

export class Many2OneFieldRotting extends Many2OneField {
    static template = "mail.Many2OneFieldRotting";

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
    ...buildM2OFieldDescription(Many2OneFieldRotting),
});
