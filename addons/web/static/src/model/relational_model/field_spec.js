// @ts-check

/** @module @web/model/relational_model/field_spec - Builds server field specifications from active fields for data fetching */

import { evalPartialContext } from "@web/core/context";
import { orderByToString } from "@web/core/utils/order_by";
function getFieldContextForSpec(activeFields, fields, fieldName, evalContext) {
    let context = activeFields[fieldName].context;
    if (!context || context === "{}") {
        context = fields[fieldName].context || {};
    } else {
        context = evalPartialContext(context, evalContext);
    }
    if (Object.keys(context).length > 0) {
        return context;
    }
}

/**
 * @param {Object} activeFields
 * @param {Object} fields
 * @param {Object} evalContext
 * @param {{ orderBys?: Object, withInvisible?: boolean }} [options]
 * @returns {Object}
 */
export function getFieldsSpec(
    activeFields,
    fields,
    evalContext,
    { orderBys, withInvisible } = {},
) {
    const fieldsSpec = {};
    const properties = [];
    for (const fieldName in activeFields) {
        if (fields[fieldName].relatedPropertyField) {
            continue;
        }
        const { related, limit, defaultOrderBy, invisible } = activeFields[fieldName];
        const isAlwaysInvisible = invisible === "True" || invisible === "1";
        fieldsSpec[fieldName] = {};
        switch (fields[fieldName].type) {
            case "one2many":
            case "many2many": {
                if (related && (withInvisible || !isAlwaysInvisible)) {
                    fieldsSpec[fieldName].fields = getFieldsSpec(
                        related.activeFields,
                        related.fields,
                        evalContext,
                        { withInvisible },
                    );
                    fieldsSpec[fieldName].context = getFieldContextForSpec(
                        activeFields,
                        fields,
                        fieldName,
                        evalContext,
                    );
                    fieldsSpec[fieldName].limit = limit;
                    const orderBy = orderBys?.[fieldName] || defaultOrderBy || [];
                    if (orderBy.length) {
                        fieldsSpec[fieldName].order = orderByToString(orderBy);
                    }
                }
                break;
            }
            case "many2one":
            case "reference": {
                fieldsSpec[fieldName].fields = {};
                if (!isAlwaysInvisible) {
                    if (related) {
                        fieldsSpec[fieldName].fields = getFieldsSpec(
                            related.activeFields,
                            related.fields,
                            evalContext,
                        );
                    }
                    fieldsSpec[fieldName].fields.display_name = {};
                    fieldsSpec[fieldName].context = getFieldContextForSpec(
                        activeFields,
                        fields,
                        fieldName,
                        evalContext,
                    );
                }
                break;
            }
            case "many2one_reference": {
                if (related && !isAlwaysInvisible) {
                    fieldsSpec[fieldName].fields = getFieldsSpec(
                        related.activeFields,
                        related.fields,
                        evalContext,
                    );
                    fieldsSpec[fieldName].context = getFieldContextForSpec(
                        activeFields,
                        fields,
                        fieldName,
                        evalContext,
                    );
                }
                break;
            }
            case "properties": {
                properties.push(fieldName);
                break;
            }
        }
    }

    for (const fieldName of properties) {
        const fieldSpec = fieldsSpec[fields[fieldName].definition_record];
        if (fieldSpec) {
            if (!fieldSpec.fields) {
                fieldSpec.fields = {};
            }
            fieldSpec.fields.display_name = {};
        }
    }
    return fieldsSpec;
}
