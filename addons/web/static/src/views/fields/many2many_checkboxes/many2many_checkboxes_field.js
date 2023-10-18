/** @odoo-module **/

import { Component, onWillUnmount } from "@odoo/owl";
import { CheckBox } from "@web/core/checkbox/checkbox";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useBus } from "@web/core/utils/hooks";
import { debounce } from "@web/core/utils/timing";
import { useSpecialData } from "@web/views/fields/relational_utils";
import { standardFieldProps } from "../standard_field_props";

export class Many2ManyCheckboxesField extends Component {
    static template = "web.Many2ManyCheckboxesField";
    static components = { CheckBox };
    static props = {
        ...standardFieldProps,
        domain: { type: Array, optional: true },
    };

    setup() {
        this.specialData = useSpecialData((orm, props) => {
            const { relation } = props.record.fields[props.name];
            return orm.call(relation, "name_search", ["", props.domain]);
        });
        // these two sets track pending changes in the relation, and allow us to
        // batch consecutive changes into a single replaceWith, thus saving
        // unnecessary potential intermediate onchanges
        this.idsToAdd = new Set();
        this.idsToRemove = new Set();
        this.debouncedCommitChanges = debounce(this.commitChanges.bind(this), 500);
        useBus(this.props.record.model.bus, "NEED_LOCAL_CHANGES", this.commitChanges.bind(this));
        onWillUnmount(this.commitChanges.bind(this));
    }

    get items() {
        return this.specialData.data;
    }

    isSelected(item) {
        return this.props.record.data[this.props.name].currentIds.includes(item[0]);
    }

    commitChanges() {
        if (this.idsToAdd.size === 0 && this.idsToRemove.size === 0) {
            return;
        }
        const result = this.props.record.data[this.props.name].addAndRemove({
            add: [...this.idsToAdd],
            remove: [...this.idsToRemove],
        });
        this.idsToAdd.clear();
        this.idsToRemove.clear();
        return result;
    }

    onChange(resId, checked) {
        if (checked) {
            if (this.idsToRemove.has(resId)) {
                this.idsToRemove.delete(resId);
            } else {
                this.idsToAdd.add(resId);
            }
        } else {
            if (this.idsToAdd.has(resId)) {
                this.idsToAdd.delete(resId);
            } else {
                this.idsToRemove.add(resId);
            }
        }
        this.debouncedCommitChanges();
    }
}

export const many2ManyCheckboxesField = {
    component: Many2ManyCheckboxesField,
    displayName: _t("Checkboxes"),
    supportedTypes: ["many2many"],
    isEmpty: () => false,
    extractProps(fieldInfo, dynamicInfo) {
        return {
            domain: dynamicInfo.domain(),
        };
    },
};

registry.category("fields").add("many2many_checkboxes", many2ManyCheckboxesField);

export function preloadMany2ManyCheckboxes(orm, record, fieldName, { domain }) {
    const field = record.fields[fieldName];
    return orm.call(field.relation, "name_search", ["", domain]);
}
