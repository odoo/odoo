import { _t } from "@web/core/l10n/translation";
import { registry } from '@web/core/registry';
import { useMatrixConfigurator } from "@product_matrix/js/matrix_configurator_hook";
import { useService } from "@web/core/utils/hooks";
import { useRecordObserver } from "@web/model/relational_model/utils";
import {
    productLabelSectionAndNoteField,
    ProductLabelSectionAndNoteField
} from "@account/components/product_label_section_and_note_field/product_label_section_and_note_field";

export class PurchaseOrderLineProductField extends ProductLabelSectionAndNoteField {
    static template = "purchase.PurchaseProductField";
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.currentValue = this.props.record.data[this.props.name];

        useRecordObserver((record) => {
            if (record.isInEdition && this.props.record.data[this.props.name]) {
                if (!this.currentValue || this.currentValue.id != record.data[this.props.name].id) {
                    // Field was updated if line was open in edit mode,
                    //      field is not emptied,
                    //      new value is different than existing value.

                    this._onProductTemplateUpdate();
                }
            }
            this.currentValue = record.data[this.props.name];
        });
        this.matrixConfigurator = useMatrixConfigurator();
    }

    get configurationButtonHelp() {
        return _t("Edit Configuration");
    }
    get isConfigurableTemplate() {
        return this.props.record.data.is_configurable_product;
    }

    async _onProductTemplateUpdate() {
        const result = await this.orm.call(
            'product.template',
            'get_single_product_variant',
            [this.props.record.data.product_template_id.id],
        );
        if(result && result.product_id) {
            if (this.props.record.data.product_id != result.product_id.id) {
                this.props.record.update({
                    // TODO right name get (same problem as configurator)
                    product_id: { id: result.product_id, display_name: result.product_name },
                });
            }
        } else {
            this.matrixConfigurator.open(this.props.record, false);
        }
    }

    onEditConfiguration() {
        if (this.props.record.data.is_configurable_product) {
            this.matrixConfigurator.open(this.props.record, true);
        }
    }
}

registry.category("fields").add("pol_product_many2one", {
    ...productLabelSectionAndNoteField,
    component: PurchaseOrderLineProductField,
});
