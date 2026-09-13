// @ts-check
/** @odoo-module native */

import { Domain } from "@web/core/domain";
import { FieldComponent } from "@web/fields/field_component";
import { fieldHandleFor } from "@web/fields/field_handle";
import { completeSelectedOptions } from "@web/fields/relational/selection_options";
import { useSpecialData } from "@web/fields/relational/special_data";
import { getFieldDomain } from "@web/model/relational_model";

export class SelectionLikeField extends FieldComponent {
    /** @type {{ data: [number, string][], isReady: boolean }} */
    specialData;

    setup() {
        this.type = this.field.type;
        if (this.type === "many2one") {
            this.specialData = useSpecialData(async (orm, props) => {
                const field = fieldHandleFor(props.record, props.name);
                const { relation } = field.definition;
                let domain = getFieldDomain(props.record, props.name, props.domain);
                const value = field.value;
                if (domain.length && value) {
                    domain = Domain.or([[["id", "=", value.id]], domain]).toList(
                        props.record.evalContext,
                    );
                }
                const context = props.context || {};
                const options = await orm.call(relation, "name_search", ["", domain], {
                    context,
                });
                return completeSelectedOptions(
                    options,
                    value ? [value.id] : [],
                    (option) => option[0],
                    (ids) =>
                        orm.call(relation, "name_search", ["", [["id", "in", ids]]], {
                            context,
                            limit: ids.length,
                        }),
                );
            });
        }
    }

    /** @returns {Array<[any, string]>} the choices a selection-like widget offers, an empty label excluded */
    get options() {
        switch (this.type) {
            case "many2one":
                return this.specialData.data;
            case "selection":
                return this.field.definition.selection.filter(
                    (/** @type {[any, string]} */ option) => option[1] !== "",
                );
            default:
                return [];
        }
    }

    get isReady() {
        return this.type !== "many2one" || this.specialData.isReady;
    }

    get string() {
        switch (this.type) {
            case "many2one":
                return this.field.value ? this.field.value.display_name : "";
            case "selection":
                return this.field.value !== false
                    ? /** @type {any} */ (
                          this.field.definition.selection.find(
                              (/** @type {any} */ o) => o[0] === this.field.value,
                          )?.[1] ?? ""
                      )
                    : "";
            default:
                return "";
        }
    }

    get value() {
        const rawValue = this.field.value;
        return this.type === "many2one" && rawValue ? rawValue.id : rawValue;
    }

    /**
     * @param {unknown} id
     * @param {Array<[any, string]>} options
     * @returns {{ id: number, display_name: string } | false | undefined}
     */
    many2oneValueFor(id, options) {
        if (id === false || id === null || id === undefined) {
            return false;
        }
        const option = options.find((option) => option[0] === id);
        return option && { id: option[0], display_name: option[1] };
    }

    stringify(/** @type {any} */ value) {
        return JSON.stringify(value);
    }
}
