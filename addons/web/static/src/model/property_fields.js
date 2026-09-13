// @ts-check
/** @odoo-module native */

import { invalidateAggregateSpecs } from "./relational_model/field_values.js";

/** @import { Field } from "@web/model/types" */

/** @import { ServiceFactories as Services } from "services" */

/**
 * @param {string} propertyFullName
 * @param {Record<string, any> | undefined | false} definition
 * @returns {Field}
 */
export function describePropertyDefinitionAsField(propertyFullName, definition) {
    const [parentFieldName] = propertyFullName.split(".");
    const described = definition && definition.type ? definition : { type: "char" };
    return {
        ...described,
        type: String(described.type),
        name: propertyFullName,
        propertyName: definition ? definition.name : undefined,
        relation: definition ? definition.comodel : undefined,
        relatedPropertyField: { name: parentFieldName },
    };
}

/**
 * @param {Services["orm"]} orm
 * @param {string} resModel
 * @param {Record<string, any>} context
 * @param {Record<string, Field>} fields
 * @param {string} propertyFullName
 * @param {() => boolean} [isCurrent] Whether this request may still publish its definition.
 * @returns {Promise<void>}
 */
export async function addPropertyFieldDef(
    orm,
    resModel,
    context,
    fields,
    propertyFullName,
    isCurrent = () => true,
) {
    let definition;
    try {
        definition = await orm.call(
            resModel,
            "get_property_definition",
            [propertyFullName],
            { context },
        );
    } catch {
        definition = undefined;
    }
    if (!isCurrent()) {
        return;
    }
    fields[propertyFullName] = describePropertyDefinitionAsField(
        propertyFullName,
        definition,
    );
    invalidateAggregateSpecs(fields);
}

/**
 * @param {Services["orm"]} orm
 * @param {string} resModel
 * @param {Record<string, any>} context
 * @param {Record<string, Field>} fields
 * @param {Iterable<string>} groupBy
 * @param {() => boolean} [isCurrent]
 * @returns {Promise<void>}
 */
export async function addPropertyFieldDefs(
    orm,
    resModel,
    context,
    fields,
    groupBy,
    isCurrent,
) {
    const proms = [];
    for (const groupByName of groupBy) {
        if (groupByName in fields) {
            continue;
        }
        const [parentFieldName] = groupByName.split(".");
        if (fields[parentFieldName]?.type !== "properties") {
            continue;
        }
        proms.push(
            addPropertyFieldDef(orm, resModel, context, fields, groupByName, isCurrent),
        );
    }
    await Promise.all(proms);
}
