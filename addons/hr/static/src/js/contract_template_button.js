/** @odoo-module **/

import { Component, useState, useRef } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { usePopover } from "@web/core/popover/popover_hook";
import { SelectionField } from "@web/views/fields/selection/selection_field";
import { Many2One, computeM2OProps } from "@web/views/fields/many2one/many2one";

class TemplateSelectionPopover extends Component {
    static template = "hr.TemplateSelectionPopover";
    static components = { Many2One };
    static props = {
        close: Function,
        onSelect: Function,
        record: Object,
        companyId: { type: Number, optional: true },
    };

    setup() {
        this.state = useState({ 
            selectedTemplate: null,
        });
    }

    get many2oneProps() {
        const companyId = this.props.companyId || this.env.services.company.currentCompany.id;
        
        const fieldProps = computeM2OProps({
            ...this.props.fieldProps,
            name: "contract_template_id",
            record: this.props.record,
            canCreate: false,
            canCreateEdit: false,
            canQuickCreate: false,
            canOpen: false,
            domain: () => [["employee_id", "=", false], ["company_id", "=", companyId]],
            context: {},
            readonly: false,
        });

        return {
            ...fieldProps,
            placeholder: "Search contract templates...",
            value: this.state.selectedTemplate,
            update: (value) => {
                this.state.selectedTemplate = value;
            }
        };
    }

    onConfirm() {
        if (this.state.selectedTemplate) {
            this.props.record.update({ contract_template_id: this.state.selectedTemplate });
        }
        this.props.close();
    }
}

export class ContractTemplateField extends SelectionField {
    static template = "hr.ContractTemplateField";
    
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.templateButtonRef = useRef("templateButton");
        this.templatePopover = usePopover(TemplateSelectionPopover, {
            closeOnClickAway: true,
            position: "bottom",
        });
    }

    async onSelectTemplate() {
        const companyId = this.props.record.data.company_id 
            ? this.props.record.data.company_id.id 
            : this.env.services.company.currentCompany.id;
        
        this.templatePopover.open(this.templateButtonRef.el, {
            fieldProps: this.props,
            record: this.props.record,
            companyId,
            onSelect: (template) => this.loadTemplate(template),
        });
    }

    async loadTemplate(templateValue) {
        await this.props.record.update({ contract_template_id: templateValue });
    }
}

export const contractTemplateField = {
    component: ContractTemplateField,
};

registry.category("fields").add("contract_template_button", contractTemplateField);
