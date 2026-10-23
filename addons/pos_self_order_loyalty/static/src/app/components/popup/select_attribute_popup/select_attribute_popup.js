import { Component, proxy, useProps, t } from "@odoo/owl";
import { useSubEnv } from "@web/owl2/utils";
import { useSelfOrder } from "@pos_self_order/app/services/self_order_service";
import { AttributeSelection } from "@pos_self_order/app/components/attribute_selection/attribute_selection";
import { AttributeSelectionHelper } from "@pos_self_order/app/components/attribute_selection/attribute_selection_helper";
import { ProductTemplate } from "@point_of_sale/app/models/product_template";
import { ProductProduct } from "@point_of_sale/app/models/product_product";

export class SelectAttributePopup extends Component {
    static template = "pos_self_order_loyalty.SelectAttributePopup";
    static components = { AttributeSelection };
    props = useProps({
        productTemplate: t.instanceOf(ProductTemplate),
        presetVariant: t.instanceOf(ProductProduct).optional(),
        getPayload: t.function(),
        close: t.function(),
    });

    setup() {
        this.selfOrder = useSelfOrder();
        useSubEnv({ selectedValues: {} });
        this.state = proxy({ selectedValues: this.env.selectedValues });

        if (this.props.presetVariant) {
            const attributesToDisplay = this.props.productTemplate.attribute_line_ids;
            const helper = new AttributeSelectionHelper(this.selfOrder, attributesToDisplay);
            for (const value of this.props.presetVariant.product_template_attribute_value_ids) {
                helper.getSelectedValues(value.attribute_line_id).add(value.id);
            }
            this.env.selectedValues[this.props.productTemplate.id] = helper;
        }
    }

    get selection() {
        return this.state.selectedValues[this.props.productTemplate.id];
    }

    hasMissingAttributeValue() {
        return Boolean(
            this.selection?.getMissingAttributeValue(this.props.productTemplate.attribute_line_ids)
        );
    }

    confirm() {
        if (this.hasMissingAttributeValue()) {
            return;
        }
        this.props.getPayload({
            attribute_value_ids: this.selection?.getAllSelectedAttributeValuesIds() || [],
            attribute_custom_values: this.selection?.getAllCustomValues() || {},
        });
        this.props.close();
    }
}
