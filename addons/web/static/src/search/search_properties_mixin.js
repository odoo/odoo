// @ts-check
/** @odoo-module native */

import { makeLogger } from "@web/core/debug/debug_logger";
import { deepEqual } from "@web/core/utils/collections/objects";

import { findGroupByGroupId } from "./search_group_by.js";

const log = makeLogger("web.search.properties");
/** @type {WeakMap<object, object>} */
const propertySearchRequests = new WeakMap();

/**
 * @param {Record<string, any>} definition
 * @param {string | undefined} definitionRecordName
 * @returns {string}
 */
function propertyDescription(definition, definitionRecordName) {
    return definitionRecordName
        ? `${definition.string} (${definitionRecordName})`
        : definition.string;
}

/**
 * A changed type or relation invalidates saved operators, values and intervals.
 * Labels and choice metadata can be refreshed without changing query identity.
 * @param {Record<string, any>} previous
 * @param {Record<string, any>} next
 */
function compatiblePropertyDefinition(previous, next) {
    return previous.type === next.type && previous.comodel === next.comodel;
}

/** @param {Record<string, any>} previous @param {Record<string, any>} next */
function compatibleGroupingDefinition(previous, next) {
    if (!compatiblePropertyDefinition(previous, next)) {
        return false;
    }
    const key =
        previous.type === "selection"
            ? "selection"
            : previous.type === "tags"
              ? "tags"
              : null;
    if (!key) {
        return true;
    }
    const choices = (/** @type {Record<string, any>} */ definition) =>
        new Map(
            (definition[key] || []).map(([value, ...metadata]) => [value, metadata]),
        );
    return deepEqual(choices(previous), choices(next));
}

/**
 * Refresh display labels without changing saved criteria, including removed choices.
 * @param {any[]} query
 * @param {number} searchItemId
 * @param {Record<string, any>} definition
 */
function refreshChoiceLabels(query, searchItemId, definition) {
    const options =
        definition.type === "selection"
            ? definition.selection
            : definition.type === "tags"
              ? definition.tags
              : [];
    const labels = new Map((options || []).map(([value, label]) => [value, label]));
    let changed = false;
    for (const item of query) {
        const value = item.autocompleteValue;
        if (
            item.searchItemId === searchItemId &&
            value &&
            labels.has(value.value) &&
            value.label !== labels.get(value.value)
        ) {
            value.label = labels.get(value.value);
            changed = true;
        }
    }
    return changed;
}

/**
 * Group-by paths cannot distinguish definition records. Keep one entry for
 * compatible names, and exclude paths whose types, relations or choices disagree.
 * The ORM resolves one definition for the entire path, so unioning choices would
 * still put values exclusive to another definition into the unset group.
 * @param {import("@web/core/field_service").PropertyDefinitionRecord[]} records
 */
function groupablePropertyRecords(records) {
    const byName = new Map();
    const ambiguous = new Set();
    for (const record of records) {
        for (const definition of record.definitions) {
            const previous = byName.get(definition.name);
            if (
                previous &&
                !compatibleGroupingDefinition(previous.definition, definition)
            ) {
                ambiguous.add(definition.name);
            }
            byName.set(definition.name, { record, definition });
        }
    }
    if (ambiguous.size) {
        log.logic("ambiguous-property-grouping", () => ({ names: [...ambiguous] }));
    }
    return [...byName.values()]
        .filter(({ definition }) => !ambiguous.has(definition.name))
        .map(({ record, definition }) => ({ ...record, definitions: [definition] }));
}

/**
 * @template {new (...args: any[]) => any} T
 * @param {T} Base
 */
export const SearchPropertiesMixin = (Base) =>
    class extends Base {
        /**
         * @param {Record<string, any>} searchItem
         * @returns {Promise<Object[]>}
         */
        async getSearchItemsProperties(searchItem) {
            if (searchItem.type !== "field" || searchItem.fieldType !== "properties") {
                return [];
            }
            const field = this.searchViewFields[searchItem.fieldName];
            const parent = this.searchItems[searchItem.id];
            if (!parent || parent.fieldName !== searchItem.fieldName || !field) {
                return [];
            }
            const definitionRecord = field.definition_record;
            const activeId = this.globalContext.active_id || false;
            const request = {};
            propertySearchRequests.set(parent, request);
            const isCurrent = () =>
                propertySearchRequests.get(parent) === request &&
                this.searchItems[searchItem.id] === parent &&
                this.searchViewFields[searchItem.fieldName] === field &&
                (this.globalContext.active_id || false) === activeId;
            const release = () => {
                if (propertySearchRequests.get(parent) === request) {
                    propertySearchRequests.delete(parent);
                }
            };
            let result;
            try {
                result = await this._fetchPropertiesDefinition(
                    this.resModel,
                    searchItem.fieldName,
                );
            } catch (error) {
                const current = isCurrent();
                release();
                if (current) {
                    throw error;
                }
                log.logic("search-definitions-superseded", () => ({
                    field: searchItem.fieldName,
                    failed: true,
                }));
                return [];
            }
            const current = isCurrent();
            release();
            if (!current) {
                log.logic("search-definitions-superseded", () => ({
                    field: searchItem.fieldName,
                    failed: false,
                }));
                return [];
            }

            let activeLabelChanged = false;
            const searchItemIds = new Set();
            const existingFieldProperties = new Map();
            for (const item of Object.values(this.searchItems)) {
                if (
                    item.type === "field_property" &&
                    item.propertyItemId === searchItem.id
                ) {
                    existingFieldProperties.set(
                        JSON.stringify([
                            item.propertyDomain[2],
                            item.propertyFieldDefinition.name,
                        ]),
                        item,
                    );
                }
            }

            for (const {
                definitionRecordId,
                definitionRecordName,
                definitions,
            } of result) {
                for (const definition of definitions) {
                    if (definition.type === "separator") {
                        continue;
                    }
                    const existingSearchItem = existingFieldProperties.get(
                        JSON.stringify([definitionRecordId, definition.name]),
                    );
                    if (
                        existingSearchItem &&
                        compatiblePropertyDefinition(
                            existingSearchItem.propertyFieldDefinition,
                            definition,
                        )
                    ) {
                        const description = propertyDescription(
                            definition,
                            definitionRecordName,
                        );
                        activeLabelChanged ||=
                            existingSearchItem.description !== description &&
                            this.query.some(
                                (item) => item.searchItemId === existingSearchItem.id,
                            );
                        // Always visit the query, even when its title already changed.
                        activeLabelChanged =
                            refreshChoiceLabels(
                                this.query,
                                existingSearchItem.id,
                                definition,
                            ) || activeLabelChanged;
                        existingSearchItem.propertyFieldDefinition = definition;
                        existingSearchItem.description = description;
                        searchItemIds.add(existingSearchItem.id);
                        continue;
                    }
                    const id = this.nextId++;
                    /** @type {Record<string, any>} */
                    const newSearchItem = {
                        id,
                        type: "field_property",
                        fieldName: searchItem.fieldName,
                        propertyDomain: [definitionRecord, "=", definitionRecordId],
                        propertyFieldDefinition: definition,
                        propertyItemId: searchItem.id,
                        description: propertyDescription(
                            definition,
                            definitionRecordName,
                        ),
                        groupId: this.nextGroupId++,
                    };
                    if (["many2many", "tags"].includes(definition.type)) {
                        newSearchItem.operator = "in";
                    }
                    this.searchItems[id] = newSearchItem;
                    searchItemIds.add(id);
                }
            }

            const staleIds = [...existingFieldProperties.values()]
                .filter((/** @type {any} */ item) => !searchItemIds.has(item.id))
                .map((/** @type {any} */ item) => item.id);
            const queryChanged = this._forgetSearchItems(staleIds);
            log.logic("search-definitions-refreshed", () => ({
                field: searchItem.fieldName,
                queryChanged,
                activeLabelChanged,
            }));
            if (queryChanged || activeLabelChanged) {
                await this._notify({ reloadSections: queryChanged });
            }
            return this.getSearchItems((/** @type {any} */ searchItem) =>
                searchItemIds.has(searchItem.id),
            );
        }

        /**
         * @param {number[]} ids
         * @returns {boolean}
         */
        _forgetSearchItems(ids) {
            for (const id of ids) {
                delete this.searchItems[id];
            }
            this._enrichedSearchItems = null;
            if (!ids.length) {
                return false;
            }
            const queryLength = this.query.length;
            const retiredIds = new Set(ids);
            this.query = this.query.filter(
                (/** @type {any} */ queryElem) =>
                    !retiredIds.has(queryElem.searchItemId),
            );
            return this.query.length !== queryLength;
        }

        async updateSearchViewItemsProperty() {
            if (!this.searchViewFields) {
                return;
            }

            const fields = Object.values(this.searchViewFields);

            /** @type {Map<string, {field: Record<string, any>, promise: Promise<void>}>} */
            const inFlight = (this._filledPropertyFields ??= new Map());

            const proms = [];
            for (const field of fields) {
                if (field.type !== "properties") {
                    continue;
                }
                const requestKey = JSON.stringify([
                    field.name,
                    this.globalContext.active_id || false,
                ]);
                let entry = inFlight.get(requestKey);
                if (!entry || entry.field !== field) {
                    const promise = this._updatePropertyFieldSearchItems(field);
                    entry = { field, promise };
                    const request = entry;
                    promise
                        .catch(() => {})
                        .finally(() => {
                            if (inFlight.get(requestKey) === request) {
                                inFlight.delete(requestKey);
                            }
                        });
                    inFlight.set(requestKey, entry);
                }
                proms.push(entry.promise);
            }
            await Promise.all(proms);
        }

        /** @param {Record<string, any>} field */
        async _updatePropertyFieldSearchItems(field) {
            const activeId = this.globalContext.active_id || false;
            const isCurrent = () =>
                this.searchViewFields[field.name] === field &&
                (this.globalContext.active_id || false) === activeId;
            let records;
            try {
                records = await this._fetchPropertiesDefinition(
                    this.resModel,
                    field.name,
                );
            } catch (error) {
                if (isCurrent()) {
                    throw error;
                }
                log.logic("group-definitions-superseded", () => ({
                    field: field.name,
                    failed: true,
                }));
                return;
            }
            if (!isCurrent()) {
                log.logic("group-definitions-superseded", () => ({
                    field: field.name,
                    failed: false,
                }));
                return;
            }
            const result = groupablePropertyRecords(records);

            const isPropertyGroupBy = (/** @type {any} */ item) =>
                item.isProperty && ["groupBy", "dateGroupBy"].includes(item.type);
            const existingByFieldName = new Map(
                Object.values(this.searchItems)
                    .filter(isPropertyGroupBy)
                    .map((/** @type {any} */ item) => [item.fieldName, item]),
            );
            let activeLabelChanged = false;
            const liveIds = new Set();
            const liveFieldNames = new Set();
            let groupByGroupId = findGroupByGroupId(this.searchItems);

            for (const {
                definitionRecordId,
                definitionRecordName,
                definitions,
            } of result) {
                for (const definition of definitions) {
                    const fullName = `${field.name}.${definition.name}`;
                    liveFieldNames.add(fullName);
                    const previousField = this.searchViewFields[fullName];
                    this.searchViewFields[fullName] = {
                        name: fullName,
                        readonly: false,
                        relation: definition.comodel,
                        required: false,
                        searchable: false,
                        selection: definition.selection,
                        sortable: true,
                        store: true,
                        string: definition.string,
                        type: definition.type,
                        relatedPropertyField: field,
                    };

                    if (["html", "separator"].includes(definition.type)) {
                        continue;
                    }
                    const existing = existingByFieldName.get(fullName);
                    if (
                        existing &&
                        previousField &&
                        compatiblePropertyDefinition(
                            {
                                type: existing.fieldType,
                                comodel: previousField.relation,
                            },
                            definition,
                        )
                    ) {
                        activeLabelChanged ||=
                            existing.description !== definition.string &&
                            this.query.some(
                                (item) => item.searchItemId === existing.id,
                            );
                        Object.assign(existing, {
                            description: definition.string,
                            definitionRecordId,
                            definitionRecordName,
                        });
                        liveIds.add(existing.id);
                        continue;
                    }
                    const id = this.nextId++;
                    this.searchItems[id] = {
                        id,
                        description: definition.string,
                        definitionRecordId,
                        definitionRecordName,
                        fieldName: fullName,
                        fieldType: definition.type,
                        isProperty: true,
                        name: `group_by_${field.name}.${definition.name}`,
                        propertyFieldName: field.name,
                        type: ["datetime", "date"].includes(definition.type)
                            ? "dateGroupBy"
                            : "groupBy",
                        groupId: (groupByGroupId ??= this.nextGroupId++),
                    };
                    liveIds.add(id);
                }
            }

            const staleIds = Object.values(this.searchItems)
                .filter(
                    (/** @type {any} */ item) =>
                        isPropertyGroupBy(item) &&
                        item.propertyFieldName === field.name &&
                        !liveIds.has(item.id),
                )
                .map((/** @type {any} */ item) => item.id);

            const prefix = `${field.name}.`;
            for (const fieldName of Object.keys(this.searchViewFields)) {
                if (fieldName.startsWith(prefix) && !liveFieldNames.has(fieldName)) {
                    delete this.searchViewFields[fieldName];
                }
            }

            const queryChanged = this._forgetSearchItems(staleIds);
            log.logic("definitions-refreshed", () => ({
                field: field.name,
                live: liveIds.size,
                retired: staleIds.length,
                queryChanged,
                activeLabelChanged,
            }));
            if (queryChanged || activeLabelChanged) {
                await this._notify({ reloadSections: queryChanged });
            }
        }

        /**
         * @param {string} resModel
         * @param {string} fieldName
         * @returns {Promise<{definitionRecordId: number, definitionRecordName: string, definitions: Record<string, any>[]}[]>}
         */
        async _fetchPropertiesDefinition(resModel, fieldName) {
            const domain = [];
            const activeId = this.globalContext.active_id;
            if (activeId) {
                domain.push(["id", "=", activeId]);
            }

            return this.fieldService.loadPropertyDefinitionsByRecord(
                resModel,
                fieldName,
                domain,
            );
        }
    };
