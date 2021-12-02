/** @odoo-module **/

import { usePopover } from "@web/core/popover/popover_hook";
import { useModelField } from "./model_field_hook";
import { ModelFieldSelectorPopover } from "./model_field_selector_popover";

const { Component } = owl;

function useUniquePopover() {
    const popover = usePopover();
    let remove = null;
    return Object.assign(Object.create(popover), {
        add(target, component, props, options) {
            if (remove) {
                remove();
            }
            remove = popover.add(target, component, props, options);
            return () => {
                remove();
                remove = null;
            };
        },
    });
}

export class ModelFieldSelector extends Component {
    setup() {
        this.popover = useUniquePopover();
        this.modelField = useModelField();
        this.chain = [];
    }
    async willStart() {
        this.chain = await this.loadChain(this.props.fieldName);
    }
    async willUpdateProps(nextProps) {
        if (this.props.fieldName !== nextProps.fieldName) {
            this.chain = await this.loadChain(nextProps.fieldName);
        }
    }

    get fieldNameChain() {
        return this.getFieldNameChain(this.props.fieldName);
    }

    getFieldNameChain(fieldName) {
        return fieldName.length ? fieldName.split(".") : [];
    }

    async loadChain(fieldName) {
        const fieldNameChain = this.getFieldNameChain(fieldName);
        let currentNode = {
            resModel: this.props.resModel,
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
            },
            {
                closeOnClickAway: true,
            }
        );
    }
}
ModelFieldSelector.template = "web._ModelFieldSelector";
ModelFieldSelector.components = {
    Popover: ModelFieldSelectorPopover,
};
ModelFieldSelector.defaultProps = {
    showSearchInput: true,
    update: () => {},
};
