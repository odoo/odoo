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
        switch (this.props.record.fields[this.props.name].type) {
            case "many2one":
                return this.props.record.data[this.props.name]
                    ? this.props.record.data[this.props.name][1]
                    : "";
            case "selection":
                return this.props.record.data[this.props.name] !== false
                    ? this.options.find((o) => o[0] === this.props.record.data[this.props.name])[1]
                    : "";
            default:
                return "";
        }
    }
    get value() {
        const rawValue = this.props.record.data[this.props.name];
        return this.props.record.fields[this.props.name].type === "many2one" && rawValue
            ? rawValue[0]
            : rawValue;
    }

    stringify(value) {
        return JSON.stringify(value);
    }

    /**
     * @param {string | number | false} value
     */
    onChange(value) {
        switch (this.props.record.fields[this.props.name].type) {
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
                if (value === this.value) {
                    this.props.record.update({ [this.props.name]: false });
                } else {
                    this.props.record.update({ [this.props.name]: value });
                }
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

export function preloadSelection(orm, record, fieldName, { domain }) {
    const field = record.fields[fieldName];
    return orm.call(field.relation, "name_search", ["", domain]);
}

registry.category("preloadedData").add("selection_badge", {
    loadOnTypes: ["many2one"],
    preload: preloadSelection,
});
