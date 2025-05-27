import { Component, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class RottingFieldForm extends Component {
    static props = {
        ...standardFieldProps,
    };
    static template = "mail.RottingFieldForm";

    setup() {
        // Preprocess all sentences as childless strings so they're easier to format in the DOM
        this.sentences = useState({
            shorthand: _t("%sd", this.props.record.data.day_rotting),
            singular: _t("Rotting: 1 day"),
            plural: _t("Rotting: %s days", this.props.record.data.day_rotting),
        });
        this.title = _t(
            "This resource has not been updated in more than %s days.",
            this.props.record.data.day_rotting
        );
    }
}

export class RottingFieldKanban extends RottingFieldForm {
    static template = "mail.RottingFieldKanban";
}

export class RottingFieldList extends RottingFieldForm {
    static template = "mail.RottingFieldList";
}

registry.category("fields").add("rotting_form", {
    component: RottingFieldForm,
});
registry.category("fields").add("rotting_kanban", {
    component: RottingFieldKanban,
});
registry.category("fields").add("rotting_list", {
    component: RottingFieldList,
    listViewWidth: [50, 100],
});
