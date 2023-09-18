/** @odoo-module */

import { Component, useState } from "@odoo/owl";

export class AttributeSelector extends Component {
    static props = ["product", "options", "line?"];

    setup() {
        this.env.attribute_components.push(this);
        this.state = useState({
            selectedValues: {},
        });

        this.initAttribute();
    }

    get attributes() {
        return this.props.product.attributes;
    }

    initAttribute() {
        const attributeMulti = [];
        const attributeSingle = [];

        for (const attr of this.attributes) {
            if (attr.display_type !== "multi") {
                attributeSingle.push(attr);
            } else {
                attributeMulti.push(attr);
            }
        }

        for (const attribute of attributeSingle) {
            if (this.props.line) {
                for (const value of attribute.values) {
                    if (this.props.line.selected_attributes.includes(value.id)) {
                        this.state.selectedValues[attribute.id] = value.id;
                    }
                }
            }

            if (!this.state.selectedValues[attribute.id]) {
                this.state.selectedValues[attribute.id] = this.props.options.defaultAttr
                    ? attribute.values[0].id
                    : false;
            }
        }

        for (const attrMulti of attributeMulti) {
            this.state.selectedValues[attrMulti.id] = {};

            for (const value of attrMulti.values) {
                if (this.props.line) {
                    if (this.props.line.selected_attributes.includes(value.id)) {
                        this.state.selectedValues[attrMulti.id][value.id] = true;
                    }
                } else {
                    this.state.selectedValues[attrMulti.id][value.id] = false;
                }
            }
        }
    }

    isChecked(attribute, value) {
        return attribute.display_type === "multi"
            ? this.state.selectedValues[attribute.id][value.id]
            : this.state.selectedValues[attribute.id] === value.id;
    }

    get selectedAttributeIds() {
        return this.attributeSelected.map((a) => a.valueIds).flat();
    }

    get attributeSelected() {
        return Object.entries(this.state.selectedValues).map(([key, value]) => {
            const attribute = this.selfOrder.attributeById[parseInt(key)];
            let valueName = "";
            let valueIds = [];

            if (value instanceof Object) {
                valueName = attribute.values
                    .filter((v) => value[v.id])
                    .map((v) => v.name)
                    .join(", ");
                valueIds = attribute.values.filter((v) => value[v.id]).map((v) => v.id);
            } else {
                valueName = attribute.values.find((v) => v.id === parseInt(value)).name;
                valueIds = [parseInt(value)];
            }

            return {
                id: attribute.id,
                name: attribute.name,
                value: valueName,
                valueIds: valueIds,
            };
        });
    }
}
