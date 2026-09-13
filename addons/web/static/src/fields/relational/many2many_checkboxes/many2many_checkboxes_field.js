// @ts-check
/** @odoo-module native */

import { onWillRender, useState } from "@odoo/owl";
import { CheckBox } from "@web/components/checkbox/checkbox";
import { _t } from "@web/core/translation";
import { registerField } from "@web/fields/_registry";
import { FieldComponent } from "@web/fields/field_component";
import { useDebouncedFieldCommit } from "@web/fields/hooks/debounced_field_commit";
import { completeSelectedOptions } from "@web/fields/relational/selection_options";
import { standardFieldProps } from "@web/fields/standard_field_props";
import { getFieldDomain } from "@web/model/relational_model";

import { useSpecialData } from "../special_data.js";

export class Many2ManyCheckboxesField extends FieldComponent {
    static template = "web.Many2ManyCheckboxesField";
    static RECORD_LIMIT = 100;
    static components = { CheckBox };
    static props = {
        ...standardFieldProps,
        domain: { type: [Array, Function], optional: true },
        context: { type: Object, optional: true },
    };

    setup() {
        this.specialData = useSpecialData(async (orm, props) => {
            const { relation } = props.record.fields[props.name];
            const domain = getFieldDomain(props.record, props.name, props.domain);
            const context = props.context || {};
            const items = await orm.call(relation, "name_search", ["", domain], {
                context,
                limit: /** @type {any} */ (this.constructor).RECORD_LIMIT,
            });
            return completeSelectedOptions(
                items,
                props.record.data[props.name].currentIds,
                (item) => item[0],
                (ids) =>
                    orm.call(relation, "name_search", ["", [["id", "in", ids]]], {
                        context,
                        limit: ids.length,
                    }),
            );
        });
        this.pending = useState({ add: [], remove: [] });
        this.debouncedCommitChanges = useDebouncedFieldCommit(
            () => this.commitChanges(),
            500,
        );
        onWillRender(() => {
            this.currentIds = new Set(this.field.value.currentIds);
        });
    }

    /** @returns {Array<[number, string]>} */
    get items() {
        return this.specialData.data;
    }

    /**
     * @param {[number, string]} item
     * @returns {boolean}
     */
    isSelected(item) {
        const id = item[0];
        if (this.pending.remove.includes(id)) {
            return false;
        }
        return this.currentIds.has(id) || this.pending.add.includes(id);
    }

    /** @returns {Promise|undefined} */
    commitChanges() {
        const { add, remove } = this.pending;
        if (!add.length && !remove.length) {
            return;
        }
        const result = this.field.value.addAndRemove({
            add: [...add],
            remove: [...remove],
        });
        this.pending.add = [];
        this.pending.remove = [];
        return result;
    }

    /**
     * @param {number} resId
     * @param {boolean} checked
     */
    onChange(resId, checked) {
        if (!this.specialData.isReady || this.props.readonly) {
            return;
        }
        const [undo, stage] = checked
            ? [this.pending.remove, this.pending.add]
            : [this.pending.add, this.pending.remove];
        const undoIndex = undo.indexOf(resId);
        if (undoIndex >= 0) {
            undo.splice(undoIndex, 1);
        } else if (!stage.includes(resId)) {
            stage.push(resId);
        }
        this.debouncedCommitChanges();
    }
}

/** @type {import("registries").FieldsRegistryItemShape} */
const many2ManyCheckboxesField = {
    component: Many2ManyCheckboxesField,
    displayName: _t("Checkboxes"),
    supportedTypes: ["many2many"],
    isEmpty: () => false,
    extractProps(fieldInfo, dynamicInfo) {
        return {
            domain: dynamicInfo.domain,
            context: dynamicInfo.context,
        };
    },
};

registerField("many2many_checkboxes", many2ManyCheckboxesField);
