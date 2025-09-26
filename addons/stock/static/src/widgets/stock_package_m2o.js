import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { computeM2OProps, Many2One } from "@web/views/fields/many2one/many2one";
import {
    buildM2OFieldDescription,
    extractM2OFieldProps,
    Many2OneField,
} from "@web/views/fields/many2one/many2one_field";

export class StockPackageMany2One extends Component {
    static template = "stock.StockPackageMany2One";
    static components = { Many2One };
    static props = {
        ...Many2OneField.props,
        displaySource: { type: Boolean },
        displayDestination: { type: Boolean },
    };

    setup() {
        this.orm = useService("orm");
        this.isDone = ["done", "cancel"].includes(this.props.record?.data?.state);
    }

    get m2oProps() {
        const props = computeM2OProps(this.props);
        return {
            ...props,
            context: {
                ...props.context,
                ...this.displayNameContext,
            },
            value: this.displayValue,
        };
    }

    get isEditing() {
        return this.props.record.isInEdition;
    }

    get displayValue() {
        const displayVal = this.props.record.data[this.props.name];
        if (this.isDone && displayVal?.display_name) {
            displayVal["display_name"] = displayVal["display_name"].split(" > ").pop();
        }
        return displayVal;
    }

    get displayNameContext() {
        return {
            show_src_package: this.props.displaySource,
            show_dest_package: this.props.displayDestination,
            is_done: this.isDone,
        };
    }
}

registry.category("fields").add("package_m2o", {
    ...buildM2OFieldDescription(StockPackageMany2One),
    extractProps(staticInfo, dynamicInfo) {
        const context = dynamicInfo.context;
        return {
            ...extractM2OFieldProps(staticInfo, dynamicInfo),
            displaySource: !!context?.show_src_package,
            displayDestination: !!context?.show_dest_package,
        };
    },
});
