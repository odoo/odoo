import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { computeM2OProps, Many2One } from "@web/views/fields/many2one/many2one";
import { buildM2OFieldDescription, Many2OneField } from "@web/views/fields/many2one/many2one_field";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";


class PackageMany2XAutocomplete extends Many2XAutocomplete {
    mapRecordToOption(record) {
        return {
            value: record.id,
            label: record.dest_complete_name ? record.dest_complete_name : record.name,
        };
    }

    get searchSpecification() {
        return {
            name: {},
            dest_complete_name: {},
            ...this.props.specification,
        };
    }
}

class PackageMany2One extends Many2One {
    static template = "stock.PackageMany2One";
    static components = {
        ...super.components,
        Many2XAutocomplete: PackageMany2XAutocomplete,
    };
}

export class StockPackageDest extends Component {
    static template = "stock.StockPackageDest";
    static components = { Many2One: PackageMany2One };
    static props = { ...Many2OneField.props };

    get m2oProps() {
        const props = computeM2OProps(this.props);
        return {
            ...props,
            value: this._getDisplayValue(),
        };
    }

    _getDisplayValue() {
        const data = this.props.record.data;
        let displayVal = data[this.props.name];
        if (data.result_package_dest_name) {
            displayVal["display_name"] = data.result_package_dest_name;
        }
        return displayVal;
    }
}

registry.category("fields").add("package_dest", {
    ...buildM2OFieldDescription(StockPackageDest),
    fieldDependencies: [
        { name: "result_package_dest_name", type: "string" },
    ],
});
