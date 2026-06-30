import { rpc } from "@web/core/network/rpc";
import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import { Component } from "@odoo/owl";

export class Many2One extends Component {
    static template = "hr_attendance.Many2One";
    static components = { AutoComplete };
    static props = {
        token: String,
        update: Function,
        value: String,
    };

    get sources() {
        return [{
            options: this.loadOptionsSource.bind(this),
            optionSlot: "option",
        }];
    }

    async loadOptionsSource(input) {
        const employeeName = input;
        const data = await rpc('/hr_attendance/get_employees_without_badge', { token: this.props.token , name: employeeName });
        if (data?.status === "success") {
            return data.employees.map(emp => ({
                data: { id: emp.id },
                label: emp.name,
                onSelect: () => this.props.update({ id: emp.id, name: emp.name }),
            }));
        }
        return [];
    }
}
