/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { standardFieldProps } from "../standard_field_props";

const { Component } = owl;

export class BadgeSelectionField extends Component {
    get string() {
        switch (this.props.type) {
            case "many2one":
                return this.props.value ? this.props.value[1] : "";
            case "selection":
                return this.props.value !== false
                    ? this.props.options.find((o) => o[0] === this.props.value)[1]
                    : "";
            default:
                return "";
        }
    }
    get value() {
        const rawValue = this.props.value;
        return this.props.type === "many2one" && rawValue ? rawValue[0] : rawValue;
    }

    stringify(value) {
        return JSON.stringify(value);
    }

    /**
     * @param {string | number | false} value
     */
    onChange(value) {
        switch (this.props.type) {
            case "many2one":
                if (value === false) {
                    this.props.update(false);
                } else {
                    this.props.update(this.props.options.find((option) => option[0] === value));
                }
                break;
            case "selection":
                this.props.update(value);
                break;
        }
    }
}

BadgeSelectionField.template = "web.BadgeSelectionField";
BadgeSelectionField.props = {
    ...standardFieldProps,
    horizontal: { type: Boolean, optional: true },
    options: Object,
};

BadgeSelectionField.displayName = _lt("Badges");
BadgeSelectionField.supportedTypes = ["many2one", "selection"];

BadgeSelectionField.isEmpty = (record, fieldName) => record.data[fieldName] === false;
BadgeSelectionField.extractProps = (fieldName, record, attrs) => {
    const getOptions = () => {
        switch (record.fields[fieldName].type) {
            case "many2one":
                // WOWL: conversion needed while we keep using the legacy model
                return Object.values(record.preloadedData[fieldName]).map((v) => {
                    return [v.id, v.display_name];
                });
            case "selection":
                return record.fields[fieldName].selection;
            default:
                return [];
        }
    };
    return {
        options: getOptions(),
    };
};

registry.category("fields").add("selection_badge", BadgeSelectionField);

export function preloadSelection(orm, record, fieldName) {
    const field = record.fields[fieldName];
    const context = record.evalContext;
    const domain = record.getFieldDomain(fieldName).toList(context);
    return orm.call(field.relation, "name_search", ["", domain]);
}

registry.category("preloadedData").add("selection_badge", {
    loadOnTypes: ["many2one"],
    preload: preloadSelection,
});
