import { Component, props, t } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { computeM2OProps, Many2One } from "@web/views/fields/many2one/many2one";
import {
    buildM2OFieldDescription,
    extractM2OFieldProps,
} from "@web/views/fields/many2one/many2one_field";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { FormViewDialog, formViewDialogProps } from "@web/views/view_dialogs/form_view_dialog";

class Many2XStockPackageAutocomplete extends Many2XAutocomplete {
    get createDialog() {
        const onRecordSave = async (record) => {
            // We need to reload to get the name computed from the backend.
            const saved = await record.save({ reload: true });
            if (saved && this.props.update) {
                // Without this, the package is named 'Unnamed' in the UI until the record is saved.
                this.props.update([{ ...record.data, id: record.resId }]);
            }
            return saved;
        };
        class PackageFormDialog extends FormViewDialog {
            props = props({
                ...formViewDialogProps,
                onRecordSave: t.function().optional(() => onRecordSave),
            });
        }
        return PackageFormDialog;
    }
}

class StockPackageMany2OneReplacer extends Many2One {
    static components = {
        ...Many2One.components,
        Many2XAutocomplete: Many2XStockPackageAutocomplete,
    };
}

export class StockPackageMany2One extends Component {
    static template = "stock.StockPackageMany2One";
    static components = { Many2One: StockPackageMany2OneReplacer };
    // Inline conversion of Many2OneField.props (still declared old-style in
    // @web/views/fields/many2one/many2one_field, without an exported schema).
    props = props({
        ...standardFieldProps,
        canCreate: t.boolean().optional(),
        canCreateEdit: t.boolean().optional(),
        canOpen: t.boolean().optional(),
        canQuickCreate: t.boolean().optional(),
        canScanBarcode: t.boolean().optional(),
        canWrite: t.boolean().optional(),
        context: t.object().optional(),
        decorations: t.object().optional(),
        domain: t.or([t.array(), t.function()]).optional(),
        nameCreateField: t.string().optional(),
        openActionContext: t.string().optional(),
        placeholder: t.string().optional(),
        searchLimit: t.number().optional(),
        searchThreshold: t.number().optional(),
        string: t.string().optional(),
        displaySource: t.boolean(),
        displayDestination: t.boolean(),
    });

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
