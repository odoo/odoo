import { rpc } from "@web/core/network/rpc";
import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import { Component } from "@odoo/owl";
import { useDebounced } from "@web/core/utils/timing";

export class Many2One extends Component {
    static template = "hr_attendance.Many2One";
    static components = { AutoComplete };
    static props = {
        token: String,
        update: Function,
        value: String,
    };

    setup() {
        this.debouncedLoadOptions = useDebounced(this.loadOptionsSource.bind(this), 200);
    }

    get sources() {
        return [
            {
                options: this.debouncedLoadOptions,
                optionSlot: "option",
            },
        ];
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
