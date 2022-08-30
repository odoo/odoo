/** @odoo-module */

const { Component } = owl;

export class ProjectProfitability extends Component {
    get revenues() {
        return this.props.data.revenues;
    }

    get costs() {
        return this.props.data.costs;
    }

    get margin() {
        const invoiced_billed = this.revenues.total.invoiced - this.costs.total.billed;
        const to_invoice_to_bill = this.revenues.total.to_invoice - this.costs.total.to_bill;
        return {
            invoiced_billed,
            to_invoice_to_bill,
            total: invoiced_billed + to_invoice_to_bill,
        };
    }
}

ProjectProfitability.props = {
    data: Object,
    labels: Object,
    formatMonetary: Function,
    onClick: Function,
};
ProjectProfitability.template = 'project.ProjectProfitability';
