/** @odoo-module **/

import {Component, useState} from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

export class KioskManualSelection extends Component {
    setup() {
        this.state = useState({
            displayedEmployees : this.props.employees,
            searchInput: ""
        });
        this.displayedEmployees = this.props.employees
    }
    onDepartementClick(dep_id){
        if (dep_id){
            this.state.displayedEmployees = this.props.employees.filter(item => item.department.id === dep_id)
        }else{
            this.state.displayedEmployees = this.props.employees
        }
    }

    onSearchInput(ev) {
        const searchInput = ev.target.value;
        if (searchInput.length){
            this.state.displayedEmployees = this.props.employees.filter(item => item.name.toLowerCase().includes(searchInput.toLowerCase()))
        }else{
            this.state.displayedEmployees = this.props.employees
        }
    }
}

KioskManualSelection.template = "hr_attendance.public_kiosk_manual_selection";
KioskManualSelection.components = {
    Dropdown,
    DropdownItem
}
KioskManualSelection.props = {
    employees : {type : Array},
    displayBackButton : {type : Boolean},
    departments: {type : Array},
    onSelectEmployee : {type : Function}
};
