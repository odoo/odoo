/** @odoo-module **/

import { useModelField } from "./model_field_hook";
import { useUniquePopover } from "./unique_popover_hook";
import { ModelFieldSelectorPopover } from "./model_field_selector_popover";

import { Component, onWillStart, onWillUpdateProps, useState } from "@odoo/owl";

export class ModelFieldSelector extends Component {
    setup() {
        this.popover = useUniquePopover();
        this.modelField = useModelField();
        this.state = useState({
            chain: [],
            fieldName: this.props.fieldName,
            isDirty: false,
        });

        onWillStart(async () => {
            this.state.chain = await this.loadChain(this.props.resModel, this.props.fieldName);
        });
        onWillUpdateProps(async (nextProps) => {
            this.state.chain = await this.loadChain(nextProps.resModel, nextProps.fieldName);
            this.state.fieldName = nextProps.fieldName;
            this.state.isDirty = false;
        });
    }

    get fieldNameChain() {
        return this.getFieldNameChain(this.state.fieldName ?? this.props.fieldName);
    }

    getFieldNameChain(fieldName) {
        return fieldName.length ? fieldName.split(".") : [];
    }

    async loadChain(resModel, fieldName) {
        if ("01".includes(fieldName)) {
            return [{ resModel, field: { string: fieldName } }];
        }
        return this.modelField.loadChain(resModel, fieldName);
    }
    async update(fieldName, isFieldSelected) {
        this.state.fieldName = fieldName;
        this.state.isDirty = !isFieldSelected;
        if (isFieldSelected) {
            await this.props.update(fieldName);
        } else {
            this.state.chain = await this.loadChain(this.props.resModel, fieldName);
        }
    }

    onFieldSelectorClick(ev) {
        if (this.props.readonly) {
            return;
        }
        this.popover.add(
            ev.currentTarget,
            this.constructor.components.Popover,
            {
                chain: this.state.chain,
                update: this.update.bind(this),
                showSearchInput: this.props.showSearchInput,
                isDebugMode: this.props.isDebugMode,
                loadChain: this.loadChain.bind(this),
                filter: this.props.filter,
                followRelations: this.props.followRelations,
            },
            {
                closeOnClickAway: true,
                popoverClass: "o_popover_field_selector",
                onClose: () => {
                    if (this.state.isDirty) {
                        this.props.update(this.state.fieldName);
                    }
                },
            }
        );
    }
}

Object.assign(ModelFieldSelector, {
    template: "web._ModelFieldSelector",
    components: {
        Popover: ModelFieldSelectorPopover,
    },
    props: {
        fieldName: String,
        resModel: String,
        readonly: { type: Boolean, optional: true },
        showSearchInput: { type: Boolean, optional: true },
        isDebugMode: { type: Boolean, optional: true },
        update: { type: Function, optional: true },
        filter: { type: Function, optional: true },
        followRelations: { type: Boolean, optional: true },
    },
    defaultProps: {
        readonly: true,
        isDebugMode: false,
        showSearchInput: true,
        update: () => {},
        filter: () => true,
        followRelations: true,
    },
});
