import { rpc } from "@web/core/network/rpc";
import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import { Component } from "@odoo/owl";
import {_t} from "@web/core/l10n/translation";

export class Many2One extends Component {
    static template = "hr_attendance.Many2One";
    static components = { AutoComplete };
    static props = {
        token: String,
        update: Function,
        value: String,
    };

    get sources() {
        return [
            {
                options: this.loadOptionsSource.bind(this),
                optionSlot: "option",
            },
        ];
    }

    async loadOptionsSource(input) {
        const employeeName = input;
        const data = await rpc("/hr_attendance/get_employees_without_badge", {
            token: this.props.token,
            name: employeeName,
        });
        let options = [];
        if (data?.status === "success") {
            options = data.employees.map(emp => ({
                data: { id: emp.id },
                label: emp.name,
                onSelect: () => this.props.update({ id: emp.id, name: emp.name }),
            }));
        }
        if (employeeName.length > 0) {
            options.push({
                label: _t("Create employee %s", employeeName),
                onSelect: () => {
                    this.props.update({ name: employeeName, isNew: true });
                },
            });
        }
        return options;
    }
}
