import { Component, useState } from '@odoo/owl';
import { Dropdown } from '@web/core/dropdown/dropdown';
import { useDropdownState } from '@web/core/dropdown/dropdown_hooks';
import { DropdownItem } from '@web/core/dropdown/dropdown_item';
import { x2ManyCommands } from "@web/core/orm_service";
import { registry } from '@web/core/registry';
import { useService } from '@web/core/utils/hooks';

export class ProductImage extends Component {
    static template = 'variant_image_assignment';
    static components = { Dropdown, DropdownItem };
    static props = {
        id: String,
        name: String,
        readonly: Boolean,
        record: Object,
    };

    setup() {
        this.orm = useService('orm');
        this.record = this.props.record;

        this.state = useState({
            attributes: [],
            checkedIds: new Set(),
        });

        this.dropdownState = useDropdownState();
    }

    get showDropdown() {
        const parent = this.record._parentRecord;
        if (!parent.resId) {
            return false;
        }
        if (this.record.data.product_tmpl_id) {
            return parent.data.product_variant_count > 1
        }
        return true;
    }

    get selectedCount() {
        return this.record.data[this.props.name].count || 0;
    }

    async beforeOpen() {
        const isNewRecord = !this.record.resId;
        const productTmplId = this.record.data.product_tmpl_id.id || this.record.context.active_id;
        const productVariantId = isNewRecord
            ? this.record.context.default_product_variant_ids?.[0]
            : false;

        const { attributes, current_value_ids } = await this.orm.call(
            'product.template',
            'get_attribute_values_for_image_assignment',
            [productTmplId, productVariantId],
        );

        this.state.attributes = attributes;

        const ids = current_value_ids.length
            ? current_value_ids
            : this.record.data[this.props.name]._currentIds;

        if (current_value_ids.length) {
            this.record.update({ [this.props.name]: [x2ManyCommands.set(current_value_ids)] });
        }
        this.state.checkedIds = new Set(ids);
    }

    toggleValue(valueId) {
        const checkedIds = this.state.checkedIds;
        const isChecked = checkedIds.has(valueId);

        isChecked ? checkedIds.delete(valueId) : checkedIds.add(valueId);

        this.record.update({
          [this.props.name]: [
            isChecked
              ? x2ManyCommands.unlink(valueId)
              : x2ManyCommands.link(valueId),
          ],
        });
    }
}

const productImage = { component: ProductImage };

registry.category('fields').add('variant_image_assignment', productImage);
