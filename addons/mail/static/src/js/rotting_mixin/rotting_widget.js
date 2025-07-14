import { Component, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import {
    badgeSelectionField,
    BadgeSelectionField,
} from "@web/views/fields/badge_selection/badge_selection_field";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class RottingFieldForm extends Component {
    static props = {
        ...standardFieldProps,
    };
    static template = "mail.RottingFieldForm";

    setup() {
        // Preprocess all sentences as childless strings so they're easier to format in the DOM
        this.sentences = useState({
            shorthand: _t("%sd", this.props.record.data.rotting_days),
            singular: _t("Rotting: 1 day"),
            plural: _t("Rotting: %s days", this.props.record.data.rotting_days),
        });
        this.title = _t(
            "This resource has not been updated in more than %s days.",
            this.props.record.data.rotting_days
        );
    }
}

export class RottingFieldKanban extends RottingFieldForm {
    static props = {
        ...standardFieldProps,
    };
    static template = "mail.RottingFieldKanban";
}

export class RottingBadgeFieldList extends BadgeSelectionField {
    static template = "mail.RottingBadgeFieldList";
    setup() {
        super.setup();
        // As this widget is appended to another field's value, we display no additional title to prevent title overlap
        this.sentences = useState({
            shorthand: _t("%sd", this.props.record.data.rotting_days),
        });
    }
}

registry.category("fields").add("rotting_form", {
    component: RottingFieldForm,
});
registry.category("fields").add("rotting_kanban", {
    component: RottingFieldKanban,
});

registry.category("fields").add("rotting_badge_list", {
    ...badgeSelectionField,
    component: RottingBadgeFieldList,
});
