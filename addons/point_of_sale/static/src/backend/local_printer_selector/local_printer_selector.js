import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { capitalize } from "@web/core/utils/strings";
import { AutoComplete } from "@web/core/autocomplete/autocomplete";

export class LocalPrinterSelector extends Component {
    static template = "point_of_sale.LocalPrinterSelector";
    static components = { AutoComplete };
    static props = {
        ...standardWidgetProps,
    };

    setup() {
        this.odooNativeApp = window.OdooNativeApp || null;
        this.state = useState({ printers: [], value: "" });
        onWillStart(async () => {
            await this._loadPrinters();
            this.state.value = this.value || "";
        });
    }

    async _loadPrinters() {
        const { status, devices = [] } = this.odooNativeApp
            ? await this.odooNativeApp.devices({ device_type: "printer" })
            : {};
        this.state.printers = status ? devices : [];
    }

    get value() {
        return this.props.record.data.local_printer_data?.display_name || "";
    }

    get sources() {
        return [
            {
                optionSlot: "printer_option",
                options: () =>
                    this.state.printers.map((printer) => ({
                        label: printer.display_name,
                        data: {
                            device_type: capitalize(printer.device_type),
                            communication_protocol: capitalize(printer.communication_protocol),
                        },
                        onSelect: () => this.onSelect(printer),
                    })),
            },
        ];
    }

    onSelect(printer) {
        this.state.value = printer.display_name;
        this.props.record.update({
            local_printer_data: printer,
        });
    }

    onInput({ inputValue }) {
        this.state.value = inputValue;
    }

    onBlur() {
        if (!this.state.printers.some((p) => p.display_name === this.state.value)) {
            this.state.value = this.value;
        }
    }
}

registry.category("fields").add("local_printer_selector", {
    component: LocalPrinterSelector,
});
