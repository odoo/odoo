import { Dialog } from "@web/core/dialog/dialog";
import { Component, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { session } from "@web/session";

/** You might wonder why I defined all these strings here and not in the template.
 * The reason is that I wanted clear templates that use a single element to render an option,
 * meaning that the label and helper text had to be defined here in the code.
 */
function getModelOptions() {
    const modelOptions = {
        use_partner: {
            label: _t("Contact details"),
            help: _t("Get contact, phone and email fields on records"),
            value: false,
        },
        use_responsible: {
            label: _t("User assignment"),
            help: _t("Assign a responsible to each record"),
            value: false,
        },
        use_date: {
            label: _t("Date & Calendar"),
            help: _t("Assign dates and visualize records in a calendar"),
            value: false,
        },
        use_double_dates: {
            label: _t("Date range & Gantt"),
            help: _t("Define start/end dates and visualize records in a Gantt chart"),
            value: false,
        },
        use_stages: {
            label: _t("Pipeline stages"),
            help: _t("Stage and visualize records in a custom pipeline"),
            value: false,
        },
        use_tags: {
            label: _t("Tags"),
            help: _t("Categorize records with custom tags"),
            value: false,
        },
        use_image: {
            label: _t("Picture"),
            help: _t("Attach a picture to a record"),
            value: false,
        },
        lines: {
            label: _t("Lines"),
            help: _t("Add details to your records with an embedded list view"),
            value: false,
        },
        use_notes: {
            label: _t("Notes"),
            help: _t("Write additional notes or comments"),
            value: false,
        },
        use_value: {
            label: _t("Monetary value"),
            help: _t("Set a price or cost on records"),
            value: false,
        },
        use_company: {
            label: _t("Company"),
            help: _t("Restrict a record to a specific company"),
            value: false,
        },
        use_sequence: {
            label: _t("Custom Sorting"),
            help: _t("Manually sort records in the list view"),
            value: true,
        },
        use_mail: {
            label: _t("Chatter"),
            help: _t("Send messages, log notes and schedule activities"),
            value: true,
        },
        use_active: {
            label: _t("Archiving"),
            help: _t("Archive deprecated records"),
            value: true,
        },
    };
    if (!session.display_switch_company_menu) {
        delete modelOptions.use_company;
    }
    return modelOptions;
}

export class ModelConfigurator extends Component {
    static template = "web_studio.ModelConfigurator";
    static components = {};
    static props = {
        embed: { type: Boolean, optional: true },
        label: { type: String },
        onConfirmOptions: Function,
        onPrevious: Function,
    };

    setup() {
        this.state = useState({ saving: false });
        this.options = useState(getModelOptions());
    }

    /**
     * Handle the confirmation of the dialog, just fires an event
     * to whoever instanciated it.
     */
    async onConfirm() {
        try {
            this.state.saving = true;

            const mappedOptions = Object.entries(this.options)
                .filter((opt) => opt[1].value)
                .map((opt) => opt[0]);

            await this.props.onConfirmOptions(mappedOptions);
        } finally {
            this.state.saving = false;
        }
    }
}

export class ModelConfiguratorDialog extends Component {
    static components = { Dialog, ModelConfigurator };
    static template = "web_studio.ModelConfiguratorDialog";

    static props = {
        confirm: { type: Function },
        close: { type: Function },
        confirmLabel: { type: String, optional: true },
    };

    async onConfirm(data) {
        await this.props.confirm(data);
        this.props.close();
    }

    onPrevious() {
        this.props.close();
    }
}
