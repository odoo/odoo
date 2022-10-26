/** @odoo-module **/

import { registry } from '@mail/model/model_core';
import { ModelField } from '@mail/model/model_field';
import { ModelInfo } from '@mail/model/model_info';

export class ModelGenerator {

    constructor(manager) {
        this.manager = manager;
    }

    /**
     * @returns {Object}
     */
    start() {
        // Create the model through a class to give it a meaningful name to be
        // displayed in stack traces and stuff.
        const model = { 'Record': class {} }['Record'];
        this._apply(model);
        // Record is generated separately and before the other models since
        // it is the dependency of all of them.
        const allModelNamesButRecord = [...registry.keys()].filter(name => name !== 'Record');
        for (const modelName of allModelNamesButRecord) {
            const model = { [modelName]: class extends this.manager.models['Record'] {} }[modelName];
            this._apply(model);
        }
        /**
         * Check that fields on the generated models are correct.
         */
        this._checkDeclared();
        /**
         * Process declared model fields definitions, so that these field
         * definitions are much easier to use in the system. For instance, all
         * relational field definitions have an inverse.
         */
        this._process();
        /**
         * Check that all model fields are correct, notably one relation
         * should have matching reversed relation.
         */
        this._checkProcessed();
        this._checkOnChanges();
    }

    /**
     * Adds fields, methods, getters, and identifyingMode from the model
     * definition to the model, then registers it in `this.manager.models`.
     *
     * @private
     * @param {Object} model
     */
    _apply(model) {
        const definition = registry.get(model.name);
        Object.assign(model, Object.fromEntries(definition.get('modelMethods')));
        Object.assign(model.prototype, Object.fromEntries(definition.get('recordMethods')));
        for (const [getterName, getter] of definition.get('modelGetters')) {
            Object.defineProperty(model, getterName, { get: getter });
        }
        for (const [getterName, getter] of definition.get('recordGetters')) {
            Object.defineProperty(model.prototype, getterName, { get: getter });
        }
        // Make model manager accessible from model.
        this.manager.modelInfos[model.name] = new ModelInfo(this.manager, { model, identifyingMode: definition.get('identifyingMode') });
        model.modelManager = this.manager;
        model.fields = {};
        this.manager.listenersAll.set(model, new Map());
        this.manager.models[model.name] = model;
    }

    /**
     * @private
     * @throws {Error} in case some declared fields are not correct.
     */
     _checkDeclared() {
        for (const model of Object.values(this.manager.models)) {
            for (const [fieldName, field] of registry.get(model.name).get('fields')) {
                // 0. Forbidden name.
                if (fieldName in model.prototype) {
                    throw new Error(`Field ${model}/${fieldName} has a forbidden name.`);
                }
                // 1. Field type is required.
                if (!(['attribute', 'relation'].includes(field.fieldType))) {
                    throw new Error(`Field ${model}/${fieldName} has unsupported type "${field.fieldType}".`);
                }
                // 2. Invalid keys based on field type.
                if (field.fieldType === 'attribute') {
                    const invalidKeys = Object.keys(field).filter(key =>
                        ![
                            'compute',
                            'default',
                            'fieldType',
                            'identifying',
                            'readonly',
                            'related',
                            'required',
                            'sum',
                        ].includes(key)
                    );
                    if (invalidKeys.length > 0) {
                        throw new Error(`Field ${model}/${fieldName} contains some invalid keys: "${invalidKeys.join(", ")}".`);
                    }
                }
                if (field.fieldType === 'relation') {
                    const invalidKeys = Object.keys(field).filter(key =>
                        ![
                            'compute',
                            'default',
                            'fieldType',
                            'identifying',
                            'inverse',
                            'isCausal',
                            'readonly',
                            'related',
                            'relationType',
                            'required',
                            'sort',
                            'to',
                        ].includes(key)
                    );
                    if (invalidKeys.length > 0) {
                        throw new Error(`Field ${model}/${fieldName} contains some invalid keys: "${invalidKeys.join(", ")}".`);
                    }
                    if (!this.manager.models[field.to]) {
                        throw new Error(`Relational field ${model}/${fieldName} targets to unknown model name "${field.to}".`);
                    }
                    if (field.required && field.relationType !== 'one') {
                        throw new Error(`Relational field ${model}/${fieldName} has "required" true with a relation of type "${field.relationType}" but "required" is only supported for "one".`);
                    }
                    if (field.sort && field.relationType !== 'many') {
                        throw new Error(`Relational field "${model}/${fieldName}" has "sort" with a relation of type "${field.relationType}" but "sort" is only supported for "many".`);
                    }
                }
                // 3. Check for redundant or unsupported attributes on identifying fields.
                if (field.identifying) {
                    if ('readonly' in field) {
                        throw new Error(`Identifying field ${model}/${fieldName} has unnecessary "readonly" attribute (readonly is implicit for identifying fields).`);
                    }
                    if ('required' in field && this.manager.modelInfos[model.name].identifyingMode === 'and') {
                        throw new Error(`Identifying field ${model}/${fieldName} has unnecessary "required" attribute (required is implicit for AND identifying fields).`);
                    }
                    if ('default' in field) {
                        throw new Error(`Identifying field ${model}/${fieldName} has "default" attribute, but default values are not supported for identifying fields.`);
                    }
                }
                // 4. Computed field.
                if (field.compute) {
                    if (typeof field.compute !== 'function') {
                        throw new Error(`Property "compute" of field ${model}/${fieldName} must be a string (instance method name) or a function (the actual compute).`);
                    }
                    if ('readonly' in field) {
                        throw new Error(`Computed field ${model}/${fieldName} has unnecessary "readonly" attribute (readonly is implicit for computed fields).`);
                    }
                }
                // 5. Related field.
                if (field.related) {
                    if (field.compute) {
                        throw new Error(`field ${model}/${fieldName} cannot be a related and compute field at the same time.`);
                    }
                    if (!(typeof field.related === 'string')) {
                        throw new Error(`Property "related" of field ${model}/${fieldName} has invalid format.`);
                    }
                    const [relationName, relatedFieldName, other] = field.related.split('.');
                    if (!relationName || !relatedFieldName || other) {
                        throw new Error(`Property "related" of field ${model}/${fieldName} has invalid format.`);
                    }
                    // find relation on self or parents.
                    let relatedRelation;
                    let targetModel = model;
                    while (this.manager.models[targetModel.name] && !relatedRelation) {
                        relatedRelation = registry.get(targetModel.name).get('fields').get(relationName);
                        targetModel = targetModel.__proto__;
                    }
                    if (!relatedRelation) {
                        throw new Error(`Related field ${model}/${fieldName} relates to unknown relation name "${relationName}".`);
                    }
                    if (relatedRelation.fieldType !== 'relation') {
                        throw new Error(`Related field ${model}/${fieldName} relates to non-relational field "${relationName}".`);
                    }
                    // Assuming related relation is valid...
                    // find field name on related model or any parents.
                    const relatedModel = this.manager.models[relatedRelation.to];
                    let relatedField;
                    targetModel = relatedModel;
                    while (this.manager.models[targetModel.name] && !relatedField) {
                        relatedField = registry.get(targetModel.name).get('fields').get(relatedFieldName);
                        targetModel = targetModel.__proto__;
                    }
                    if (!relatedField) {
                        throw new Error(`Related field ${model}/${fieldName} relates to unknown related model field "${relatedFieldName}".`);
                    }
                    if (relatedField.fieldType !== field.fieldType) {
                        throw new Error(`Related field ${model}/${fieldName} has mismatched type with its related model field.`);
                    }
                    if (
                        relatedField.fieldType === 'relation' &&
                        relatedField.to !== field.to
                    ) {
                        throw new Error(`Related field ${model}/${fieldName} has mismatched target model name with its related model field.`);
                    }
                    if ('readonly' in field) {
                        throw new Error(`Related field ${model}/${fieldName} has unnecessary "readonly" attribute (readonly is implicit for related fields).`);
                    }
                }
            }
        }
    }

    /**
     * @private
     * @throws {Error}
     */
    _checkOnChanges() {
        for (const model of Object.values(this.manager.models)) {
            for (const { dependencies, methodName } of registry.get(model.name).get('onChanges')) {
                for (const dependency of dependencies) {
                    let currentModel = model;
                    let currentField;
                    for (const fieldName of dependency) {
                        if (!currentModel) {
                            throw new Error(`OnChange '${methodName}' defines a dependency with path '${dependency.join('.')}', but this dependency does not resolve: ${currentField} is not a relational field, therefore there is no relation to follow.`);
                        }
                        currentField = this.manager.modelInfos[currentModel.name].fieldMap.get(fieldName);
                        if (!currentField) {
                            throw new Error(`OnChange '${methodName}' defines a dependency with path '${dependency.join('.')}', but this path does not resolve: ${currentModel}/${fieldName} does not exist.`);
                        }
                        if (currentField.to) {
                            currentModel = this.manager.models[currentField.to];
                        } else {
                            currentModel = undefined;
                        }
                    }
                }
            }
        }
    }

    /**
     * @private
     * @throws {Error} in case some fields are not correct.
     */
    _checkProcessed() {
        for (const model of Object.values(this.manager.models)) {
            if (!['and', 'xor'].includes(this.manager.modelInfos[model.name].identifyingMode)) {
                throw new Error(`Unsupported identifying mode "${this.manager.modelInfos[model.name].identifyingMode}" on ${model}. Must be one of 'and' or 'xor'.`);
            }
            for (const field of this.manager.modelInfos[model.name].fieldList) {
                const fieldName = field.fieldName;
                if (!(['attribute', 'relation'].includes(field.fieldType))) {
                    throw new Error(`${field} has unsupported type "${field.fieldType}".`);
                }
                if (field.compute && field.related) {
                    throw new Error(`${field} cannot be a related and compute field at the same time.`);
                }
                if (field.fieldType === 'attribute') {
                    continue;
                }
                if (!field.relationType) {
                    throw new Error(`${field} must define a relation type in "relationType".`);
                }
                if (!(['many', 'one'].includes(field.relationType))) {
                    throw new Error(`${field} has invalid relation type "${field.relationType}".`);
                }
                if (!field.inverse) {
                    throw new Error(`${field} must define an inverse relation name in "inverse".`);
                }
                if (!field.to) {
                    throw new Error(`${field} must define a model name in "to" (1st positional parameter of relation field helpers).`);
                }
                const relatedModel = this.manager.models[field.to];
                if (!relatedModel) {
                    throw new Error(`${field} defines a relation to model ${field.to}, but there is no model registered with this name.`);
                }
                const inverseField = this.manager.modelInfos[relatedModel.name].fieldMap.get(field.inverse);
                if (!inverseField) {
                    throw new Error(`${field} defines its inverse as field ${relatedModel}/${field.inverse}, but it does not exist.`);
                }
                if (inverseField.inverse !== fieldName) {
                    throw new Error(`The name of ${field} does not match with the name defined in its inverse ${inverseField}.`);
                }
                if (![model.name, 'Record'].includes(inverseField.to)) {
                    throw new Error(`${field} has its inverse ${inverseField} referring to an invalid model (${inverseField.to}).`);
                }
                if (field.sort) {
                    for (const path of field.sortedFieldSplittedPaths) {
                        let currentField = field;
                        for (const fieldName of path) {
                            if (!currentField.to) {
                                throw new Error(`Field ${field} defines a sort with path '${path.join('.')}', but this path does not resolve: ${currentField} is not a relational field, therefore there is no relation to follow.`);
                            }
                            if (!this.manager.modelInfos[currentField.to].fieldMap.has(fieldName)) {
                                throw new Error(`Field ${field} defines a sort with path '${path.join('.')}', but this path does not resolve: ${this.manager.models[currentField.to]}/${fieldName} does not exist.`);
                            }
                            currentField = this.manager.modelInfos[currentField.to].fieldMap.get(fieldName);
                        }
                    }
                }
            }
            for (const identifyingField of this.manager.modelInfos[model.name].identifyingFieldNames) {
                const field = this.manager.modelInfos[model.name].fieldMap.get(identifyingField);
                if (!field) {
                    throw new Error(`Identifying field "${model}/${identifyingField}" is not a field on ${model}.`);
                }
                if (field.to) {
                    if (field.relationType !== 'one') {
                        throw new Error(`Identifying field "${model}/${identifyingField}" has a relation of type "${field.relationType}" but identifying field is only supported for "one".`);
                    }
                    const relatedModel = this.manager.models[field.to];
                    const inverseField = this.manager.modelInfos[relatedModel.name].fieldMap.get(field.inverse);
                    if (!inverseField.isCausal) {
                        throw new Error(`Identifying field "${model}/${identifyingField}" has an inverse "${inverseField}" not declared as "isCausal".`);
                    }
                }
            }
        }
    }

    /**
     * @private
     * @param {Object} model
     * @param {ModelField} field
     * @returns {ModelField}
     */
    _makeInverse(model, field) {
        const inverseField = new ModelField(this.manager, Object.assign(
            {},
            ModelField.many(model.name, { inverse: field.fieldName }),
            {
                fieldName: `_inverse_${model}/${field.fieldName}`,
                // Allows the inverse of an identifying field to be
                // automatically generated.
                isCausal: field.identifying,
                model: this.manager.models[field.to],
            },
        ));
        return inverseField;
    }

    /**
     * This function processes definition of declared fields in provided models.
     * Basically, models have fields declared in static prop `fields`, and this
     * function processes and modifies them in place so that they are fully
     * configured. For instance, model relations need bi-directional mapping, but
     * inverse relation may be omitted in declared field: this function auto-fill
     * this inverse relation.
     *
     * @private
     */
    _process() {
        /**
         * 1. Prepare fields.
         */
        for (const model of Object.values(this.manager.models)) {
            const sumContributionsByFieldName = new Map();
            // Make fields aware of their field name.
            for (const [fieldName, fieldData] of registry.get(model.name).get('fields')) {
                model.fields[fieldName] = new ModelField(this.manager, Object.assign({}, fieldData, {
                    fieldName,
                    model,
                }));
                if (fieldData.sum) {
                    const [relationFieldName, contributionFieldName] = fieldData.sum.split('.');
                    if (!sumContributionsByFieldName.has(relationFieldName)) {
                        sumContributionsByFieldName.set(relationFieldName, []);
                    }
                    sumContributionsByFieldName.get(relationFieldName).push({
                        from: contributionFieldName,
                        to: fieldName,
                    });
                }
            }
            for (const [fieldName, sumContributions] of sumContributionsByFieldName) {
                model.fields[fieldName].sumContributions = sumContributions;
            }
        }
        /**
         * 2. Auto-generate definitions of undeclared inverse relations.
         */
        for (const model of Object.values(this.manager.models)) {
            for (const field of Object.values(model.fields)) {
                if (field.fieldType !== 'relation') {
                    continue;
                }
                if (field.inverse) {
                    // Automatically make causal the inverse of an identifying.
                    if (field.identifying) {
                        this.manager.models[field.to].fields[field.inverse].isCausal = true;
                    }
                    continue;
                }
                const relatedModel = this.manager.models[field.to];
                const inverseField = this._makeInverse(model, field);
                field.inverse = inverseField.fieldName;
                relatedModel.fields[inverseField.fieldName] = inverseField;
            }
        }
        /**
         * 3. Extend definition of fields of a model with the definition of
         * fields of its parents.
         */
        for (const model of Object.values(this.manager.models)) {
            for (const field of Object.values(model.fields)) {
                this.manager.modelInfos[model.name].combinedFields[field.fieldName] = field;
            }
            let TargetModel = model.__proto__;
            while (TargetModel && TargetModel.fields) {
                for (const targetField of Object.values(TargetModel.fields)) {
                    const field = this.manager.modelInfos[model.name].combinedFields[targetField.fieldName];
                    if (!field) {
                        this.manager.modelInfos[model.name].combinedFields[targetField.fieldName] = targetField;
                    }
                }
                TargetModel = TargetModel.__proto__;
            }
        }
        /**
         * 4. Register final fields and make field accessors, to redirects field
         * access to field getter and to prevent field from being written
         * without calling update (which is necessary to process update cycle).
         */
        for (const model of Object.values(this.manager.models)) {
            // Object with fieldName/field as key/value pair, for quick access.
            this.manager.modelInfos[model.name].fieldMap = new Map(Object.entries(this.manager.modelInfos[model.name].combinedFields));
            // List of all fields, for iterating.
            this.manager.modelInfos[model.name].fieldList = [...this.manager.modelInfos[model.name].fieldMap.values()];
            this.manager.modelInfos[model.name].requiredFieldList = this.manager.modelInfos[model.name].fieldList.filter(
                field => field.required
            );
            for (const [fieldName, field] of this.manager.modelInfos[model.name].fieldMap) {
                if (field.identifying) {
                    this.manager.modelInfos[model.name].identifyingFieldNames.add(fieldName);
                }
                // Add field accessors.
                Object.defineProperty(model.prototype, fieldName, {
                    get: function getFieldValue() { // this is bound to record
                        const record = (
                            this.modelManager.isDebug
                            ? this.modelManager.recordInfos[this.localId].proxifiedRecord
                            : this.modelManager.recordInfos[this.localId].nonProxifiedRecord
                        );
                        if (this.modelManager._listeners.size) {
                            let entryRecord = this.modelManager.recordInfos[record.localId].listenersOnRecord;
                            const reason = record.modelManager.isDebug && `getField - ${field} of ${record}`;
                            let entryField = this.modelManager.recordInfos[record.localId].listenersOnField.get(field);
                            if (!entryField) {
                                entryField = new Map();
                                this.modelManager.recordInfos[record.localId].listenersOnField.set(field, entryField);
                            }
                            for (const listener of record.modelManager._listeners) {
                                listener.records.add(record);
                                const info = { listener, reason };
                                if (entryRecord.has(listener)) {
                                    entryRecord.get(listener).push(info);
                                } else {
                                    entryRecord.set(listener, [info]);
                                }
                                if (!listener.fields.has(record)) {
                                    listener.fields.set(record, new Set());
                                }
                                listener.fields.get(record).add(field);
                                if (entryField.has(listener)) {
                                    entryField.get(listener).push(info);
                                } else {
                                    entryField.set(listener, [info]);
                                }
                            }
                        }
                        return field.get(record);
                    },
                });
            }
            delete this.manager.modelInfos[model.name].combinedFields;
        }
    }

}
