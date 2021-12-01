/** @odoo-module **/

import { registry } from "@web/core/registry";
import { groupBy } from "../core/utils/arrays";
import { standardFieldProps } from "./standard_field_props";

const { Component } = owl;

export class StatusBarField extends Component {
    get isDisabled() {
        return !this.props.options.clickable;
    }

    getVisibleMany2Ones() {
        const items = this.props.record.preloadedData
            ? this.props.record.preloadedData[this.props.name]
            : [];
        return items.map((item) => ({
            ...item,
            isSelected: this.props.value && item.id === this.props.value[0],
        }));
    }

    getVisibleSelection() {
        let selection = this.props.record.fields[this.props.name].selection;
        const { statusbarVisible } = this.props.attrs;
        if (statusbarVisible) {
            const visibleSelection = statusbarVisible.trim().split(/\s*,\s*/g);
            selection = selection.filter(
                (item) => visibleSelection.includes(item[0]) || item[0] === this.props.value
            );
        }
        return selection.map((item) => ({
            id: item[0],
            name: item[1],
            isSelected: item[0] === this.props.value,
            isFolded: false,
        }));
    }

    computeItems() {
        let items = null;
        if (this.props.type === "many2one") {
            items = this.getVisibleMany2Ones();
        } else {
            items = this.getVisibleSelection();
        }

        const groups = groupBy(items, (item) => item.isSelected || !item.isFolded);
        return {
            folded: groups.false || [],
            unfolded: groups.true || [],
        };
    }

    selectItem(item) {
        switch (this.props.type) {
            case "many2one":
                this.props.update([item.id, item.name]);
                break;
            case "selection":
                this.props.update(item.id);
                break;
        }
    }

    onDropdownItemSelected(ev) {
        this.selectItem(ev.detail.payload);
    }
    onItemSelected(item) {
        this.selectItem(item);
    }
}

Object.assign(StatusBarField, {
    template: "web.StatusBarField",
    props: {
        ...standardFieldProps,
    },
    isEmpty() {
        return false;
    },
});

registry.category("fields").add("statusbar", StatusBarField);

async function fetchStatusBarPreloadedData(datapoint, fieldName) {
    const field = datapoint.fields[fieldName];
    if (field.type !== "many2one") {
        return null;
    }

    const fieldNames = ["id"];
    const foldField = datapoint.activeFields[fieldName].options.fold_field;
    if (foldField) {
        fieldNames.push(foldField);
    }

    const orm = datapoint.model.orm;
    const records = await orm.searchRead(field.relation, [], fieldNames);
    const foldMap = {};
    for (const record of records) {
        foldMap[record.id] = record[foldField];
    }

    const nameGets = await orm.call(field.relation, "name_get", [
        records.map((record) => record.id),
    ]);
    return nameGets.map((nameGet) => ({
        id: nameGet[0],
        name: nameGet[1],
        isFolded: foldField ? foldMap[nameGet[0]] : false,
    }));
}

registry.category("preloadedData").add("statusbar", fetchStatusBarPreloadedData);
