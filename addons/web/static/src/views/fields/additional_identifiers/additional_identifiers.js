/** @odoo-module */

import { Component, proxy } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { debounce } from "@web/core/utils/timing";
import { useRecordObserver } from "@web/model/relational_model/utils";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

/**
 * This widget is only used for the 'additional_identifiers' JSON field of the 'res.partner'
 * form view. It displays the additional identifiers for a partner.
 */

const METADATA_FIELD = "available_additional_identifiers_metadata";

function parseJson(value) {
    if (!value) {
        return {};
    }
    try {
        return typeof value === "string" ? JSON.parse(value) : { ...value };
    } catch {
        return {};
    }
}

export class AdditionalIdentifiersCommon extends Component {
    static template = "";
    static props = { ...standardFieldProps };

    setup() {
        super.setup();

        this.state = proxy({
            identifiers: parseJson(this.props.record.data[this.props.name]),
            metadata: parseJson(this.props.record.data[METADATA_FIELD]),
        });

        this.debouncedCommitChanges = debounce(this.commitChanges.bind(this), 50);

        useRecordObserver((record) => {
            this.state.identifiers = parseJson(record.data[this.props.name]);
            this.state.metadata = parseJson(record.data[METADATA_FIELD]);
        });
    }

    commitChanges() {
        this.props.record.update({ [this.props.name]: this.state.identifiers });
    }
}

export class AdditionalIdentifiersButton extends AdditionalIdentifiersCommon {
    static template = "web.AdditionalIdentifiersButton";
    static components = { Dropdown, DropdownItem };

    get identifiersInDropdown() {
        const typesInUse = Object.keys(this.state.identifiers);
        // 'display_optional' types are never offered in the dropdown: 'show' ones
        // are rendered directly in the list, 'hide' ones are not proposed at all.
        return Object.entries(this.state.metadata)
            .filter(([k, v]) => !typesInUse.includes(k) && !v.display_optional)
            .map(([k, v]) => ({
                identifierType: k,
                label: v.label || k,
                help: v.help || "",
                sequence: v.sequence || 100,
            }))
            .sort((a, b) => a.sequence - b.sequence);
    }

    onAdd(identifierType) {
        this.state.identifiers[identifierType] = "";
        this.debouncedCommitChanges();
    }
}

export class AdditionalIdentifiersList extends AdditionalIdentifiersCommon {
    static template = "web.AdditionalIdentifiersList";

    get sortedIdentifiers() {
        const identifiers = { ...this.state.identifiers };
        // Identifiers flagged 'show' are always rendered in the list, ready to be
        // filled, even when they have no value yet.
        for (const [identifierType, meta] of Object.entries(this.state.metadata)) {
            if (meta.display_optional === "show" && !(identifierType in identifiers)) {
                identifiers[identifierType] = "";
            }
        }
        return Object.entries(identifiers).sort(([keyA, _valA], [keyB, _valB]) => {
            const seqA = this.state.metadata[keyA]?.sequence || 100;
            const seqB = this.state.metadata[keyB]?.sequence || 100;
            return seqA - seqB;
        });
    }

    getTooltipInfo(help) {
        return JSON.stringify({ field: { help } });
    }

    onUpdateValue(identifierType, event) {
        const currentVal = event.target.value.trim();
        if (currentVal === "") {
            delete this.state.identifiers[identifierType];
        } else {
            this.state.identifiers[identifierType] = currentVal;
        }
        this.debouncedCommitChanges();
    }
}

const metadataFieldDependency = [{ name: METADATA_FIELD, type: "json", readonly: true }];

export const additionalIdentifiersButton = {
    component: AdditionalIdentifiersButton,
    supportedTypes: ["json"],
    fieldDependencies: metadataFieldDependency,
};

export const additionalIdentifiersList = {
    component: AdditionalIdentifiersList,
    supportedTypes: ["json"],
    fieldDependencies: metadataFieldDependency,
};

registry.category("fields").add("additional_identifiers_button", additionalIdentifiersButton);
registry.category("fields").add("additional_identifiers_list", additionalIdentifiersList);
