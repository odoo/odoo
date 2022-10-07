/** @odoo-module **/

import { useModelField } from "./model_field_hook";
import { useUniquePopover } from "./unique_popover_hook";
import { ModelFieldSelectorPopover } from "./model_field_selector_popover";

const { Component, onWillStart, onWillUpdateProps } = owl;

export class ModelFieldSelector extends Component {
    setup() {
        this.popover = useUniquePopover();
        this.modelField = useModelField();
        this.chain = [];

        onWillStart(async () => {
            this.chain = await this.loadChain(this.props.resModel, this.props.fieldName);
        });
        onWillUpdateProps(async (nextProps) => {
            this.chain = await this.loadChain(nextProps.resModel, nextProps.fieldName);
        });
    }

    get fieldNameChain() {
        return this.getFieldNameChain(this.props.fieldName);
    }

    getFieldNameChain(fieldName) {
        return fieldName.length ? fieldName.split(".") : [];
    }

    async loadChain(resModel, fieldName) {
        if ("01".includes(fieldName)) {
            return [{ resModel, field: { string: fieldName } }];
        }
        const fieldNameChain = this.getFieldNameChain(fieldName);
        let currentNode = {
            resModel,
            field: null,
        };
        const chain = [currentNode];
        for (const fieldName of fieldNameChain) {
            const fieldsInfo = await this.modelField.loadModelFields(currentNode.resModel);
            Object.assign(currentNode, {
                field: { ...fieldsInfo[fieldName], name: fieldName },
            });
            if (fieldsInfo[fieldName].relation) {
                currentNode = {
                    resModel: fieldsInfo[fieldName].relation,
                    field: null,
                };
                chain.push(currentNode);
            }
        }
        return chain;
    }
    update(chain) {
        this.props.update(chain.join("."));
    }

    onFieldSelectorClick(ev) {
        if (this.props.readonly) {
            return;
        }
        this.popover.add(
            ev.currentTarget,
            this.constructor.components.Popover,
            {
                chain: this.chain,
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
