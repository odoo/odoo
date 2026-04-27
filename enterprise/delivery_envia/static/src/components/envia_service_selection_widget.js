/** @odoo-module */
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { Component, useState } from "@odoo/owl";

export class EnviaServiceSelectionWidget extends Component {
    static template = "delivery_envia.EnviaServiceWidget";
    static components = {
        Dropdown,
        DropdownItem,
    };
    static props = {
        "*": true,
    };

    setup() {
        this.all_services = this.props.record.data.available_services;
        this.available_carriers = [... new Set(this.all_services.map(item => item.carrier_name))];

        this.code = this.props.record.data.selected_service_code;
        this.carrier = this.props.record.data.selected_carrier_code;

        if (this.code === "") {
            this.code = this.all_services[0].name;
            this.carrier = this.all_services[0].carrier_name;
            this.props.record.update({
                selected_service_code: this.code,
                selected_carrier_code: this.carrier,
            });
        }

        this.state = useState({
            'code': this.code,
            'carrier': this.carrier,
        });
    }

    get activeService() {
        let service = this.availableServices.find(service => service.name === this.state.code);
        if (service === undefined) {
            service = this.availableServices[0];
        }
        return service;
    }

    get availableServices() {
        return this.all_services.filter((service) => service.carrier_name == this.state.carrier);
    }

    get activeCarrier() {
        return this.available_carriers.find((carrier) => carrier == this.state.carrier).toUpperCase();
    }

    _onCarrierSelected(carrier) {
        this.state.carrier = carrier;
        this.props.record.update({ selected_carrier_code: carrier });
        this._onServiceSelected(this.activeService.name);
    }

    _onServiceSelected(code) {
        this.state.code = code;
        this.props.record.update({ selected_service_code: code });
    }
}

export const enviaServiceSelectionWidget = {
    component: EnviaServiceSelectionWidget,
};

registry.category("fields").add("envia_service_selection", enviaServiceSelectionWidget);
