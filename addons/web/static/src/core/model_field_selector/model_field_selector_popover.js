/** @odoo-module **/

import { sortBy } from "../utils/arrays";
import { useModelField } from "./model_field_hook";

import { fuzzyLookup } from "@web/core/utils/search";
import { useAutofocus } from "../utils/hooks";

import { Component, onWillStart } from "@odoo/owl";

export class ModelFieldSelectorPopover extends Component {
    setup() {
        this.chain = Array.from(this.props.chain);
        this.modelField = useModelField();
        this.unfilteredFields = {};
        this.fields = {};
        this.fieldKeys = [];
        this.currentActiveFieldId = 0;
        this.searchValue = "";
        this.defaultValue = "";
        this.isDefaultValueVisible = false;
        this.fullFieldName = this.fieldNameChain.join(".");
        if (!this.env.isSmall) {
            useAutofocus();
            useAutofocus({ refName: 'autofocusDefaultValue', selectAll: true });
        }

        onWillStart(async () => {
            await this.loadFields();
        });
    }

    get currentActiveField() {
        return this.fieldKeys[this.currentActiveFieldId];
    }

    get currentNode() {
        return this.chain[this.chain.length - 1];
    }
    get currentFieldName() {
        const nodes = this.chain.filter((node) => node.field);
        return nodes.length ? nodes[nodes.length - 1].field.string : "";
    }

    get fieldNameChain() {
        return this.chain.filter((node) => node.field).map((node) => node.field.name);
    }

    async loadFields() {
        this.unfilteredFields = await this.modelField.loadModelFields(this.currentNode.resModel);
        this.fields = {...this.unfilteredFields};
        this.fieldKeys = this.sortedKeys(this.fields);
        for (let key of this.fieldKeys) {
            const field = this.fields[key];
            if (!field.searchable || !this.props.filter(field)) {
                delete this.fields[key];
            }
        }
        this.fieldKeys = this.sortedKeys(this.fields);
    }
    sortedKeys(obj) {
        const keys = Object.keys(obj);
        return sortBy(keys, (key) => obj[key].string);
    }
    async update() {
        const fieldNameChain = this.fieldNameChain;
        this.fullFieldName = fieldNameChain.join(".");
        await this.props.update(fieldNameChain);
        await this.loadFields();
        this.render();
    }

    async onInputKeydown(ev) {
        switch (ev.key) {
            case "ArrowUp":
                ev.preventDefault();
                ev.stopPropagation();
                if (this.currentActiveFieldId> 0) {
                    this.currentActiveFieldId--;
                    await this.render();
                }
                break;
            case "ArrowDown":
                ev.preventDefault();
                ev.stopPropagation();
                if (this.currentActiveFieldId < this.fieldKeys.length-1) {
                    this.currentActiveFieldId++;
                    await this.render();
                }
                break;
            case "ArrowLeft":
                ev.preventDefault();
                ev.stopPropagation();
                this.onPreviousBtnClick();
                break;
            case "Escape":
                ev.preventDefault();
                ev.stopPropagation();
                this.props.close();
                break;
            case "Enter":
            case "ArrowRight":
                ev.preventDefault();
                ev.stopPropagation();
                if (this.isDefaultValueVisible) {
                    this.selectDefaultValue(true);
                } else {
                    const field = { ...this.fields[this.currentActiveField], name: this.currentActiveField }
                    this.onFieldSelected(field);
                }
                break;
        }
    }
    onSearch(ev) {
        this.searchValue = ev.target.value;
        let fieldKeys = this.sortedKeys(this.fields);
        if (this.searchValue) {
            fieldKeys = fuzzyLookup(this.searchValue, fieldKeys, (key) => this.fields[key].string);
        }
        this.fieldKeys = fieldKeys;
        this.render();
    }
    onDefaultValue(ev) {
        this.defaultValue = ev.target.value;
        this.render();
    }
    onPreviousBtnClick() {
        this.searchValue = "";
        if (this.currentNode.field === null) {
            this.chain.pop();
        }
        this.currentNode.field = null;
        this.update();
    }
    onFieldSelected(field) {
        this.searchValue = "";
        this.currentActiveFieldId = 0;
        this.currentNode.field = field;
        if (field.relation && this.props.followRelations) {
            this.chain.push({
                resModel: field.relation,
                field: null,
            });
            this.update();
        } else if(this.props.needDefaultValue) {
            this.isDefaultValueVisible = true;
            this.render();
            this.update();
        } else {
            this.update();
            this.props.close();
            this.props.validate(this.fieldNameChain, this.defaultValue);
        }
    }
    selectDefaultValue (acceptDefaultValue) {
        if (!acceptDefaultValue) {
            this.defaultValue = "";
        }
        this.props.close();
        this.update();
        this.props.validate(this.fieldNameChain, this.defaultValue);
    }
    async onFieldNameChange(ev) {
        this.fullFieldName = ev.target.value.replace(/\s+/g, "");
        const { resModel } = this.props.chain[0];
        try {
            this.chain = await this.props.loadChain(resModel, this.fullFieldName);
            this.update();
        } catch (_error) {
            // WOWL TODO: rethrow error when not the expected type
            this.chain = [{ resModel, field: null }];
            await this.props.update([]);
            this.render();
        }
    }
}

ModelFieldSelectorPopover.defaultProps = {
    validate: () => {},
    needDefaultValue: false,
    isDebugMode: false,
    followRelations: true,
};

ModelFieldSelectorPopover.props = {
    chain: Array,
    update: Function,
    showSearchInput: Boolean,
    isDebugMode: { type: Boolean, optional: true},
    loadChain: Function,
    filter: Function,
    close: Function,
    followRelations: { type: Boolean, optional: true },
    needDefaultValue: { type: Boolean, optional: true},
    validate: { type: Function, optional: true},
};

ModelFieldSelectorPopover.template =  "web.ModelFieldSelectorPopover";
