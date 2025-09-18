// @ts-check

/** @module @web/search/search_properties - Property-field search logic for lazy-loading definitions and creating search items */

/**
 * Extracted property-field search logic for SearchModel.
 *
 * Handles lazy loading of properties definitions, creation of
 * property-based search items and group-by items. All functions
 * receive the SearchModel instance as first argument (delegation
 * pattern), preserving subclass polymorphism.
 */

/** @import { SearchModel } from "@web/search/search_model" */

/**
 * Generate search items corresponding to properties of a field.
 *
 * Fetches property definitions for the given search item's field,
 * creates or updates field_property search items, and returns
 * the matching items.
 *
 * @param {SearchModel} searchModel - the SearchModel instance
 * @param {Object} searchItem - a search item of type "field" with fieldType "properties"
 * @returns {Promise<Object[]>} matching search items
 */

import { groupBy } from "@web/core/utils/collections/arrays";
export async function getSearchItemsProperties(searchModel, searchItem) {
    if (searchItem.type !== "field" || searchItem.fieldType !== "properties") {
        return [];
    }
    const field = searchModel.searchViewFields[searchItem.fieldName];
    const definitionRecord = field.definition_record;
    const result = await searchModel._fetchPropertiesDefinition(
        searchModel.resModel,
        searchItem.fieldName,
    );

    const searchItemIds = new Set();
    const existingFieldProperties = {};
    for (const item of Object.values(searchModel.searchItems)) {
        if (item.type === "field_property" && item.propertyItemId === searchItem.id) {
            existingFieldProperties[item.propertyFieldDefinition.name] = item;
        }
    }

    for (const { definitionRecordId, definitionRecordName, definitions } of result) {
        for (const definition of definitions) {
            if (definition.type === "separator") {
                continue;
            }
            const existingSearchItem = existingFieldProperties[definition.name];
            if (existingSearchItem) {
                // already in the list, can happen if we unfold the properties field
                // open a form view, edit the property and then go back to the search view
                // the label of the property might have been changed
                existingSearchItem.description = `${definition.string} (${definitionRecordName})`;
                searchItemIds.add(existingSearchItem.id);
                continue;
            }
            const id = searchModel.nextId++;
            const newSearchItem = {
                id,
                type: "field_property",
                fieldName: searchItem.fieldName,
                propertyDomain: [definitionRecord, "=", definitionRecordId],
                propertyFieldDefinition: definition,
                propertyItemId: searchItem.id,
                description: definitionRecordName
                    ? `${definition.string} (${definitionRecordName})`
                    : definition.string,
                groupId: searchModel.nextGroupId++,
            };
            if (["many2many", "tags"].includes(definition.type)) {
                newSearchItem.operator = "in";
            }
            searchModel.searchItems[id] = newSearchItem;
            searchItemIds.add(id);
        }
    }

    return searchModel.getSearchItems((searchItem) => searchItemIds.has(searchItem.id));
}

/**
 * Lazily populate search view items for properties fields.
 *
 * Fetches property definitions via RPC and creates group-by items
 * for each property, also registering them in searchViewFields.
 *
 * @param {SearchModel} searchModel - the SearchModel instance
 */
export async function fillSearchViewItemsProperty(searchModel) {
    if (!searchModel.searchViewFields) {
        return;
    }

    const fields = Object.values(searchModel.searchViewFields);

    for (const field of fields) {
        if (field.type !== "properties") {
            continue;
        }

        const result = await searchModel._fetchPropertiesDefinition(
            searchModel.resModel,
            field.name,
        );

        const searchItemsNames = Object.values(searchModel.searchItems)
            .filter(
                (item) =>
                    item.isProperty && ["groupBy", "dateGroupBy"].includes(item.type),
            )
            .map((item) => item.fieldName);

        for (const {
            definitionRecordId,
            definitionRecordName,
            definitions,
        } of result) {
            // some properties might have been deleted
            const groupNames = definitions.map(
                (definition) => `group_by_${field.name}.${definition.name}`,
            );
            Object.values(searchModel.searchItems).forEach((searchItem) => {
                if (
                    searchItem.isProperty &&
                    searchItem.definitionRecordId === definitionRecordId &&
                    ["groupBy", "dateGroupBy"].includes(searchItem.type) &&
                    !groupNames.includes(searchItem.name)
                ) {
                    // we can not just remove the element from the list because index are used as id
                    // so we use a different type to hide it everywhere (until the user refresh his
                    // browser and the item won't be created again)
                    searchItem.type = "group_by_property_deleted";
                }
            });

            for (const definition of definitions) {
                // we need the definition of the "field" (fake field, property) to be
                // in searchViewFields to be able to have the type, it's description, etc
                // the name of the property is stored as "<properties field name>.<property name>"
                const fullName = `${field.name}.${definition.name}`;
                searchModel.searchViewFields[fullName] = {
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

                if (
                    !searchItemsNames.includes(fullName) &&
                    !["html", "separator"].includes(definition.type)
                ) {
                    const groupByItem = {
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
                    };
                    searchModel._createGroupOfSearchItems([groupByItem]);
                }
            }
        }
    }
}

/**
 * Fetch property definitions for a given model and field.
 *
 * @param {SearchModel} searchModel - the SearchModel instance
 * @param {string} resModel - the model name
 * @param {string} fieldName - the properties field name
 * @returns {Promise<Object[]>} array of { definitionRecordId, definitionRecordName, definitions }
 */
export async function fetchPropertiesDefinition(searchModel, resModel, fieldName) {
    const domain = [];
    if (searchModel.context.active_id) {
        // assume the active id is the definition record
        // and show only its properties
        domain.push(["id", "=", searchModel.context.active_id]);
    }

    const definitions = await searchModel.fieldService.loadPropertyDefinitions(
        resModel,
        fieldName,
        domain,
    );
    const result = groupBy(
        Object.values(definitions),
        (definition) => definition.record_id,
    );
    return Object.entries(result).map(([recordId, definitions]) => ({
        definitionRecordId: parseInt(recordId),
        definitionRecordName: definitions[0]?.record_name,
        definitions,
    }));
}
