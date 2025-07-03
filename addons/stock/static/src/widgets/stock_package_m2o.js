import { Component, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { computeM2OProps, Many2One } from "@web/views/fields/many2one/many2one";
import {
    buildM2OFieldDescription,
    extractM2OFieldProps,
    Many2OneField,
} from "@web/views/fields/many2one/many2one_field";


class PackageMany2One extends Many2One {
    static template = "stock.PackageMany2One";
}

export class StockPackageMany2One extends Component {
    static template = "stock.StockPackageMany2One";
    static components = { Many2One: PackageMany2One };
    static props = {
        ...Many2OneField.props,
        displaySource: { type: Boolean },
        displayDestination: { type: Boolean },
    };

    setup() {
        this.orm = useService("orm");
        this.isDone = ['done', 'cancel'].includes(this.props.record?.data?.state)

        onWillStart(async () => {
            if (!this.props.record.data[this.props.name]?.id) {
                // If field is empty, no need to change its displayed value
                return;
            }
            const res = await this.orm.webRead(
                "stock.package",
                [this.props.record.data[this.props.name].id],
                {
                    specification: {
                        display_name: {},
                    },
                    context: { ...this.displayNameContext },
                },
            );
            if (res.length) {
                this.packageName = res[0].display_name;
            }
        });
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

    get displayValue() {
        const displayVal = this.props.record.data[this.props.name];
        if (this.isDone && this.packageName) {
            displayVal["display_name"] = this.packageName;
            // Should only be used at load. Context is correctly applied in further searches.
            this.packageName = false;
        }
        return displayVal;
    }

    get displayNameContext() {
        return {
            show_src_package: this.props.displaySource,
            show_dest_package: this.props.displayDestination,
            is_done: this.isDone,
        }
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
