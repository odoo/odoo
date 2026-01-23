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
        if (!this.record.resId) {
            return false;
        }

        if (this.record.data.product_tmpl_id && this.record._parentRecord?.resModel === 'product.template') {
            return this.record._parentRecord.data.attribute_line_ids.count > 0;
        }
        return true;
    }

    async beforeOpen() {
        this.state.attributes = await this.orm.call(
            'product.image',
            'get_attribute_values_for_image_assignment',
            [this.record.resId],
        );

        this.state.checkedIds = new Set(
            this.record.data[this.props.name].resIds || []
        );
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
