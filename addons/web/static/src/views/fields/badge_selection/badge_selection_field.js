/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { standardFieldProps } from "../standard_field_props";

import { Component } from "@odoo/owl";

export class BadgeSelectionField extends Component {
    static template = "web.BadgeSelectionField";
    static props = {
        ...standardFieldProps,
    };

    get options() {
        switch (this.props.record.fields[this.props.name].type) {
            case "many2one":
                // WOWL: conversion needed while we keep using the legacy model
                return Object.values(this.props.record.preloadedData[this.props.name]).map((v) => {
                    return [v.id, v.display_name];
                });
            case "selection":
                return this.props.record.fields[this.props.name].selection;
            default:
                return [];
        }
    }

    get string() {
        switch (this.props.type) {
            case "many2one":
                return this.props.value ? this.props.value[1] : "";
            case "selection":
                return this.props.value !== false
                    ? this.options.find((o) => o[0] === this.props.value)[1]
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
                    this.props.record.update({ [this.props.name]: false });
                } else {
                    this.props.record.update({
                        [this.props.name]: this.options.find((option) => option[0] === value),
                    });
                }
                break;
            case "selection":
                this.props.record.update({ [this.props.name]: value });
                break;
        }
    }
}

export const badgeSelectionField = {
    component: BadgeSelectionField,
    displayName: _lt("Badges"),
    supportedTypes: ["many2one", "selection"],
    isEmpty: (record, fieldName) => record.data[fieldName] === false,
    legacySpecialData: "_fetchSpecialMany2ones",
};

registry.category("fields").add("selection_badge", badgeSelectionField);

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
