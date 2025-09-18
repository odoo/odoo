// @ts-check

/** @module @web/fields/selection/selection_like_field - Abstract base class for selection-like fields with special data loading */

import { Component } from "@odoo/owl";
import { useSpecialData } from "@web/fields/relational/special_data";
import { getFieldDomain } from "@web/model/relational_model/utils";

/**
 * Base class for selection-like fields that can target either a `selection`
 * or a `many2one` ORM field type (badge, radio, plain selection).
 *
 * Provides:
 *   - type detection in `setup()`
 *   - `useSpecialData` for many2one options loaded via `name_search`
 *   - `get string()`, `get value()`, `stringify()` — identical across subclasses
 *
 * Subclasses must implement:
 *   - static template
 *   - static props
 *   - get options()
 *   - onChange()
 */
export class SelectionLikeField extends Component {
    setup() {
        this.type = this.props.record.fields[this.props.name].type;
        if (this.type === "many2one") {
            this.specialData = useSpecialData((orm, props) => {
                const { relation } = props.record.fields[props.name];
                const domain = getFieldDomain(props.record, props.name, props.domain);
                return orm.call(relation, "name_search", ["", domain]);
            });
        }
    }

    get string() {
        switch (this.type) {
            case "many2one":
                return this.props.record.data[this.props.name]
                    ? this.props.record.data[this.props.name].display_name
                    : "";
            case "selection":
                return this.props.record.data[this.props.name] !== false
                    ? /** @type {any} */ (
                          this.options.find(
                              (o) => o[0] === this.props.record.data[this.props.name],
                          )?.[1] ?? ""
                      )
                    : "";
            default:
                return "";
        }
    }

    get value() {
        const rawValue = this.props.record.data[this.props.name];
        return this.type === "many2one" && rawValue ? rawValue.id : rawValue;
    }

    stringify(value) {
        return JSON.stringify(value);
    }
}
