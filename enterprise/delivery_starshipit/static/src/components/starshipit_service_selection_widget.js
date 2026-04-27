/** @odoo-module */
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { Component, useState } from "@odoo/owl";

export class StarshipitServiceSelectionWidget extends Component {
    static template = "delivery_starshipit.StarshipitServiceWidget";
    static components = {
        Dropdown,
        DropdownItem,
    };
    static props = {
        "*": true,
    };

    setup() {
        this.available_services = this.props.record.data.available_services;
        this.code = this.props.record.data.selected_service_code
        if (this.code === "") {
            this.code = this.available_services[0].service_code;
            this.props.record.update({ [this.props.name]: this.code });
        }
        this.state = useState({
            'code': this.code,
        });
    }

    get activeService() {
        let service = this.available_services.find(service => service.service_code === this.state.code);
        if (service === undefined) {
            service = this.available_services[0];
        }
        return service;
    }

    _onSelected(code) {
        this.state.code = code;
        this.props.record.update({ [this.props.name]: code });
    }
}

export const starshipitServiceSelectionWidget = {
    component: StarshipitServiceSelectionWidget,
};

registry.category("fields").add("starshipit_service_selection", starshipitServiceSelectionWidget);
