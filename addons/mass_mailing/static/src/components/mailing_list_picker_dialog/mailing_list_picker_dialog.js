import { Component, onWillStart } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { useState } from "@web/owl2/utils";
import { MailingListTemplatePickerSheet } from "../mailing_list_template_picker_sheet/mailing_list_template_picker_sheet";
import { MailingListTypePickerSheet } from "../mailing_list_type_picker_sheet/mailing_list_type_picker_sheet";

export class MailingListPickerDialog extends Component {
    static template = "mass_mailing.MailingListPickerDialog";
    static components = {
        Dialog,
        MailingListTypePickerSheet,
        MailingListTemplatePickerSheet,
    };
    static props = {
        close: { type: Function, optional: true },
    };

    setup() {
        super.setup();
        this.orm = useService("orm");
        this.action = useService("action");
        this.listTypes = useState({});
        this.templates = useState({});

        onWillStart(async () => {
            const listTypes = await this.orm.call(
                "mailing.list",
                "get_mailing_list_types_info",
                []
            );
            const templates = await this.orm.call(
                "mailing.list",
                "get_mailing_list_templates_info",
                []
            );

            Object.assign(this.listTypes, listTypes);
            Object.assign(this.templates, templates);
        });
    }

    /**
     * Open the mailing list view that corresponds to the selected type (dynamic or manual).
     *
     * @param {string} listTypeName
     */
    async onChooseListType(listTypeName) {
        const functionName = this.listTypes[listTypeName].function;
        if (!functionName) {
            return;
        }
        const action = await this.orm.call("mailing.list", functionName, [[]]);
        if (!action) {
            return;
        }
        this.action.doAction(action);
        this.props.close();
    }

    /**
     * Opens a mailing list creation form with the domain of the selected template
     * set by default.
     *
     * @param {string} templateName the template identifier. Eg: 'recent_sign_ups'.
     */
    async onChooseListTemplate(templateName) {
        const functionName = this.templates[templateName].function;

        if (!functionName) {
            return;
        }
        const action = await this.orm.call("mailing.list", functionName, [[], templateName]);
        if (!action) {
            return;
        }
        this.action.doAction(action);
        this.props.close();
    }
}
