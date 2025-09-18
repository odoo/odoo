// @ts-check

/** @module @web/model/relational_model/utils - Barrel re-export of field metadata, spec, values, and context utilities for external consumers */

// Barrel re-export — preserves backward compatibility for all external consumers.
// Internal consumers (within model/relational_model/) use direct imports.

export {
    getBasicEvalContext,
    getFieldContext,
    getFieldDomain,
    getId,
    isRelational,
} from "./field_context";
export {
    addFieldDependencies,
    combineModifiers,
    completeActiveFields,
    createPropertyActiveField,
    extractFieldsFromArchInfo,
    makeActiveField,
    patchActiveFields,
} from "./field_metadata";
export { getFieldsSpec } from "./field_spec";
export {
    AGGREGATABLE_FIELD_TYPES,
    extractInfoFromGroupData,
    fromUnityToServerValues,
    getAggregateSpecifications,
    getGroupServerValue,
    parseServerValue,
} from "./field_values";
