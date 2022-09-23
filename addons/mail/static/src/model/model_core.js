/** @odoo-module **/

import { makeDeferred } from '@mail/utils/deferred';

/**
 * Module that contains registry for adding new models or patching models.
 * Useful for model manager in order to generate models.
 *
 * This code is not in model manager because other JS modules should populate
 * a registry, and it's difficult to ensure availability of the model manager
 * when these JS modules are deployed.
 */

export const registry = new Map();
export const IS_RECORD = Symbol("Record");

const patches = [];

/**
 * Concats `contextMessage` at the beginning of any error raising when calling
 * `func`.
 *
 * @param {Function} func The (fallible) function to be called.
 * @param {string} contextMessage Extra explanations to be added to the error
 * message if any.
 * @throws {Error} enriched with `contextMessage` if `func` raises an error.
 */
function addContextToErrors(func, contextMessage) {
    try {
        func();
    } catch (error) {
        error.message = contextMessage + error.message;
        throw error;
    }
}

/**
 * Adds the provided fields to the model specified by the `modelName`.
 *
 * @param {string} modelName The name of the model to which to add the fields.
 * @param {Object} fields Fields to be added. key = field name, value = field attributes
 */
function addFields(modelName, fields) {
    if (!registry.has(modelName)) {
        throw new Error(`Cannot add fields to model "${modelName}": model must be registered before fields can be added.`);
    }
    const definition = registry.get(modelName);
    for (const [fieldName, field] of Object.entries(fields)) {
        addContextToErrors(() => {
            assertNameIsAvailableOnRecords(fieldName, definition);
        }, `Cannot add field "${fieldName}" to model "${modelName}": `);
        definition.get('fields').set(fieldName, field);
    }
}

/**
 * Adds the provided hooks to the model specified by the `modelName`.
 *
 * @param {string} modelName The name of the model to which to add the hooks.
 * @param {Object} hooks Hooks to be added. key = name, value = handler
 */
function addLifecycleHooks(modelName, hooks) {
    if (!registry.has(modelName)) {
        throw new Error(`Cannot add lifecycle hooks to model "${modelName}": model must be registered before lifecycle hooks can be added.`);
    }
    const definition = registry.get(modelName);
    for (const [name, handler] of Object.entries(hooks)) {
        addContextToErrors(() => {
            assertIsFunction(handler);
            assertIsValidHookName(name);
            assertSectionDoesNotHaveKey('lifecycleHooks', name, definition);
        }, `Cannot add lifecycle hook "${name}" to model "${modelName}": `);
        definition.get('lifecycleHooks').set(name, handler);
    }
}

/**
 * Adds the provided model getters to the model specified by the `modelName`.
 *
 * @deprecated Getters are only used in `Record` and are intended to
 * provide fields such as `env` to all models by inheritance. The creation of
 * these fields will be directly in the model manager in the future.
 * Use fields instead.
 * @param {string} modelName The name of the model to which to add the model getters.
 * @param {Object} modelGetters Model getters to be added. key = name, value = getter
 */
function addModelGetters(modelName, modelGetters) {
    if (!registry.has(modelName)) {
        throw new Error(`Cannot add record getters to model "${modelName}": model must be registered before record getters can be added.`);
    }
    const definition = registry.get(modelName);
    for (const [getterName, getter] of Object.entries(modelGetters)) {
        addContextToErrors(() => {
            assertIsFunction(getter);
            assertNameIsAvailableOnModel(getterName, definition);
        }, `Cannot add model getter "${getterName}" to model "${modelName}": `);
        definition.get('modelGetters').set(getterName, getter);
    }
}

/**
 * Adds the provided model methods to the model specified by the `modelName`.
 *
 * @param {string} modelName The name of the model to which to add the model methods.
 * @param {Object} modelMethods Model methods to be added. key = name, value = method
 */
function addModelMethods(modelName, modelMethods) {
    if (!registry.has(modelName)) {
        throw new Error(`Cannot add model methods to model "${modelName}": model must be registered before model methods can be added.`);
    }
    const definition = registry.get(modelName);
    for (const [name, method] of Object.entries(modelMethods)) {
        addContextToErrors(() => {
            assertIsFunction(method);
            assertNameIsAvailableOnModel(name, definition);
        }, `Cannot add model method "${name}" to model "${modelName}": `);
        definition.get('modelMethods').set(name, method);
    }
}

/**
 * Adds the provided onChanges to the model specified by the `modelName`.
 *
 * @param {string} modelName The name of the model to which to add onChanges.
 * @param {Object[]} onChanges Array of onChange definitions.
 */
function addOnChanges(modelName, onChanges) {
    addContextToErrors(() => {
        if (!registry.has(modelName)) {
            throw new Error(`model must be registered before onChanges can be added.`);
        }
        for (const onChange of onChanges) {
            if (!Object.prototype.hasOwnProperty.call(onChange, 'dependencies')) {
                throw new Error("at least one onChange definition lacks dependencies (the list of fields to be watched for changes).");
            }
            if (!Object.prototype.hasOwnProperty.call(onChange, 'methodName')) {
                throw new Error("at least one onChange definition lacks a methodName (the name of the method to be called on change).");
            }
            if (!Array.isArray(onChange.dependencies)) {
                throw new Error("onChange dependencies must be an array of strings.");
            }
            if (typeof onChange.methodName !== 'string') {
                throw new Error("onChange methodName must be a string.");
            }
            const allowedKeys = ['dependencies', 'methodName'];
            for (const key of Object.keys(onChange)) {
                if (!allowedKeys.includes(key)) {
                    throw new Error(`unknown key "${key}" in onChange definition. Allowed keys: ${allowedKeys.join(", ")}.`);
                }
            }
            // paths of dependencies are splitted now to avoid having to do it
            // each time the path is followed.
            const splittedDependencies = [];
            for (const dependency of onChange.dependencies) {
                if (typeof dependency !== 'string') {
                    throw new Error("onChange dependencies must be an array of strings.");
                }
                splittedDependencies.push(dependency.split('.'));
            }
            onChange.dependencies = splittedDependencies;
        }
    }, `Cannot add onChanges to model "${modelName}": `);
    registry.get(modelName).get('onChanges').push(...onChanges);
}

/**
 * Adds the provided record methods to the model specified by the `modelName`.
 *
 * @param {string} modelName The name of the model to which to add the methods.
 * @param {Object} recordMethods Record methods to be added. key = name, value = method
 */
function addRecordMethods(modelName, recordMethods) {
    if (!registry.has(modelName)) {
        throw new Error(`Cannot add record methods to model "${modelName}": model must be registered before record methods can be added.`);
    }
    const definition = registry.get(modelName);
    for (const [name, method] of Object.entries(recordMethods)) {
        addContextToErrors(() => {
            assertIsFunction(method);
            assertNameIsAvailableOnRecords(name, definition);
        }, `Cannot add record method "${name}" to model "${modelName}": `);
        definition.get('recordMethods').set(name, method);
    }
}

/**
 * Adds the provided record getters to the model specified by the `modelName`.
 *
 * @deprecated Getters are only used in `Record` and are intended to
 * provide fields such as `env` to all records by inheritance. The creation of
 * these fields will be directly in the model manager in the future.
 * Use fields instead.
 * @param {string} modelName The name of the model to which to add the record getters.
 * @param {Object} recordGetters Record getters to be added. key = name, value = getter
 */
function addRecordGetters(modelName, recordGetters) {
    if (!registry.has(modelName)) {
        throw new Error(`Cannot add record getters to model "${modelName}": model must be registered before record getters can be added.`);
    }
    const definition = registry.get(modelName);
    for (const [getterName, getter] of Object.entries(recordGetters)) {
        addContextToErrors(() => {
            assertIsFunction(getter);
            assertNameIsAvailableOnRecords(getterName, definition);
        }, `Cannot add record getter "${getterName}" to model "${modelName}": `);
        definition.get('recordGetters').set(getterName, getter);
    }
}

/**
 * Asserts that `toAssert` is typeof function.
 *
 * @param {any} toAssert
 * @throws {Error} when `toAssert` is not typeof function.
 */
function assertIsFunction(toAssert) {
    if (typeof toAssert !== 'function') {
        throw new Error(`"${toAssert}" must be a function`);
    }
}

/**
 * Asserts that `name` is a valid hook name.
 *
 * @param {string} name The hook name to check.
 * @throws {Error} if name is not an existing hook name.
 */
function assertIsValidHookName(name) {
    const validHookNames = ['_created', '_willDelete'];
    if (!validHookNames.includes(name)) {
        throw new Error(`unsupported hook name. Possible values: ${validHookNames.join(", ")}.`);
    }
}

/**
 * Asserts that the provided `key` is not already defined within the section
 * `sectionName` on the model `modelDefinition`.
 *
 * @param {string} sectionName The section of the `modelDefinition` to check into.
 * @param {string} key The key to check for.
 * @param {Object} modelDefinition The definition of the model to check.
 */
function assertSectionDoesNotHaveKey(sectionName, key, modelDefinition) {
    if (modelDefinition.get(sectionName).has(key)) {
        throw new Error(`"${key}" is already defined on "${sectionName}".`);
    }
}

/**
 * Asserts that `name` is not already used as a key on the model.
 *
 * @param {string} name The name of the key to check the availability.
 * @param {Map} modelDefinition The model definition to look into.
 * @throws {Error} when `name` is already used as a key on the model.
 */
function assertNameIsAvailableOnModel(name, modelDefinition) {
    if (['modelGetters', 'modelMethods'].some(x => modelDefinition.get(x).has(name))) {
        throw new Error(`there is already a key with this name on the model.`);
    }
}

/**
 * Asserts that `name` is not already used as a key on the records.
 *
 * @param {string} name The name of the key to check the availability.
 * @param {Map} modelDefinition The model definition to look into.
 * @throws {Error} when `name` is already used as a key on the records.
 */
function assertNameIsAvailableOnRecords(name, modelDefinition) {
    if (['fields', 'recordGetters', 'recordMethods'].some(x => modelDefinition.get(x).has(name))) {
        throw new Error(`there is already a key with this name on the records.`);
    }
}

function patchFields(patch) {
    const newFieldsToAdd = Object.create(null);
    for (const [fieldName, fieldData] of Object.entries(patch.fields)) {
        const originalFieldDefinition = registry.get(patch.name).get('fields').get(fieldName);
        if (!originalFieldDefinition) {
            newFieldsToAdd[fieldName] = fieldData;
        } else {
            for (const [attributeName, attributeData] of Object.entries(fieldData))
                switch (attributeName) {
                    case 'compute':
                        if (!originalFieldDefinition.compute) {
                            throw new Error(`Cannot patch compute of field ${patch.name}/${fieldName}: the field is not a compute in the original definition.`);
                        }
                        if (typeof attributeData !== 'function') {
                            throw new Error(`Cannot patch compute of field ${patch.name}/${fieldName}: the compute must be a function (found: "${typeof attributeData}").`);
                        }
                        const computeBeforePatch = originalFieldDefinition.compute;
                        originalFieldDefinition.compute = function () {
                            this._super = computeBeforePatch;
                            return attributeData.call(this);
                        };
                        break;
                    case 'sort':
                        if (originalFieldDefinition.sort) {
                            if (typeof attributeData !== 'function') {
                                throw new Error(`Cannot patch sorting rules of field ${patch.name}/${fieldName}: the value of 'sort' must be a function to apply to the sorting rules array (found: "${typeof attributeData}").`);
                            }
                            originalFieldDefinition.sort = attributeData.call({ _super: originalFieldDefinition.sort });
                        } else {
                            if (!Array.isArray(attributeData)) {
                                throw new Error(`Cannot add sorting rules to field ${patch.name}/${fieldName}: sorting rules must be an array.`);
                            }
                            originalFieldDefinition.sort = attributeData;
                        }
                        break;
                    default:
                        throw new Error(`Cannot patch field ${patch.name}/${fieldName}: unsupported field attribute "${attributeName}".`);
                }
        }
    }
    addFields(patch.name, newFieldsToAdd);
}

function patchLifecycleHooks(patch) {
    const originalLifecycleHooksDefinition = registry.get(patch.name).get('lifecycleHooks');
    const newLifecycleHooksToAdd = Object.create(null);
    for (const [hookName, hookHandler] of Object.entries(patch.lifecycleHooks)) {
        if (!originalLifecycleHooksDefinition.has(hookName)) {
            newLifecycleHooksToAdd[hookName] = hookHandler;
        } else {
            if (typeof hookHandler !== 'function') {
                throw new Error(`Cannot patch hook "${hookName}" on model ${patch.name}: the hook handler must be a function (current type: "${typeof hookHandler}").`);
            }
            const hookHandlerBeforePatch = originalLifecycleHooksDefinition.get(hookName);
            originalLifecycleHooksDefinition.set(hookName, function () {
                this._super = hookHandlerBeforePatch;
                return hookHandler.call(this);
            });
        }
    }
    addLifecycleHooks(patch.name, newLifecycleHooksToAdd);
}

function patchModelMethods(patch) {
    const originalModelMethodsDefinition = registry.get(patch.name).get('modelMethods');
    const newModelMethodsToAdd = Object.create(null);
    for (const [methodName, method] of Object.entries(patch.modelMethods)) {
        if (!originalModelMethodsDefinition.has(methodName)) {
            newModelMethodsToAdd[methodName] = method;
        } else {
            if (typeof method !== 'function') {
                throw new Error(`Cannot patch model method "${methodName}" on model ${patch.name}: the method must be a function (current type: "${typeof method}").`);
            }
            const methodBeforePatch = originalModelMethodsDefinition.get(methodName);
            originalModelMethodsDefinition.set(methodName, function (...args) {
                this._super = methodBeforePatch;
                return method.call(this, ...args);
            });
        }
    }
    addModelMethods(patch.name, newModelMethodsToAdd);
}

function patchRecordMethods(patch) {
    const originalRecordMethods = registry.get(patch.name).get('recordMethods');
    const newRecordMethodsToAdd = Object.create(null);
    for (const [methodName, method] of Object.entries(patch.recordMethods)) {
        if (!originalRecordMethods.has(methodName)) {
            newRecordMethodsToAdd[methodName] = method;
        } else {
            if (typeof method !== 'function') {
                throw new Error(`Cannot patch record method "${methodName}" on model ${patch.name}: the method must be a function (current type: "${typeof method}").`);
            }
            const methodBeforePatch = originalRecordMethods.get(methodName);
            originalRecordMethods.set(methodName, function (...args) {
                this._super = methodBeforePatch;
                return method.call(this, ...args);
            });
        }
    }
    addRecordMethods(patch.name, newRecordMethodsToAdd);
}

/**
 * @param {Object} definition The JSON definition of the model to register.
 * @param {Object} [definition.fields]
 * @param {string} [definition.identifyingMode='and']
 * @param {Object} [definition.lifecycleHooks]
 * @param {Object} [definition.modelGetters] Deprecated; use fields instead.
 * @param {Object} [definition.modelMethods]
 * @param {string} definition.name
 * @param {Object[]} [definition.onChanges]
 * @param {Object} [definition.recordGetters] Deprecated; use fields instead.
 * @param {Object} [definition.recordMethods]
 */
export function registerModel({ fields, identifyingMode = 'and', lifecycleHooks, modelGetters, modelMethods, name, onChanges, recordGetters, recordMethods }) {
    if (!name) {
        throw new Error("Model is lacking a name.");
    }
    if (registry.has(name)) {
        throw new Error(`Cannot register model "${name}": model has already been registered.`);
    }
    const sectionNames = ['name', 'identifyingMode', 'lifecycleHooks', 'modelMethods', 'modelGetters', 'recordMethods', 'recordGetters', 'fields', 'onChanges'];
    const invalidSectionNames = Object.keys(arguments[0]).filter(x => !sectionNames.includes(x));
    if (invalidSectionNames.length > 0) {
        throw new Error(`Cannot register model "${name}": model definition contains unknown key(s): ${invalidSectionNames.join(", ")}`);
    }
    registry.set(name, new Map([
        ['name', name],
        ['identifyingMode', identifyingMode],
        ['lifecycleHooks', new Map()],
        ['modelMethods', new Map()],
        ['modelGetters', new Map()],
        ['recordMethods', new Map()],
        ['recordGetters', new Map()],
        ['fields', new Map()],
        ['onChanges', []],
    ]));
    if (lifecycleHooks) {
        addLifecycleHooks(name, lifecycleHooks);
    }
    if (modelMethods) {
        addModelMethods(name, modelMethods);
    }
    if (modelGetters) {
        addModelGetters(name, modelGetters);
    }
    if (recordMethods) {
        addRecordMethods(name, recordMethods);
    }
    if (recordGetters) {
        addRecordGetters(name, recordGetters);
    }
    if (fields) {
        addFields(name, fields);
    }
    if (onChanges) {
        addOnChanges(name, onChanges);
    }
}

export function registerPatch({ fields, lifecycleHooks, modelMethods, name, onChanges, recordMethods }) {
    if (!name) {
        throw new Error("Patch is lacking the name of the model to be patched.");
    }
    const allowedSectionNames = ['name', 'lifecycleHooks', 'modelMethods', 'recordMethods', 'fields', 'onChanges'];
    const invalidSectionNames = Object.keys(arguments['0']).filter(x => !allowedSectionNames.includes(x));
    if (invalidSectionNames.length > 0) {
        throw new Error(`Error while registering patch for model "${name}": patch definition contains unsupported key(s): ${invalidSectionNames.join(", ")}`);
    }
    patches.push({
        name,
        lifecycleHooks: lifecycleHooks || {},
        modelMethods: modelMethods || {},
        recordMethods: recordMethods || {},
        fields: fields || {},
        onChanges: onChanges || [],
    });
}

export const patchesAppliedPromise = makeDeferred();

(async function applyPatches() {
    if (document.readyState !== 'complete') {
        await new Promise(resolve => {
            /**
             * Called when all JS resources are loaded. This is useful to
             * ensure all definitions have been parsed before applying patches.
             */
            window.addEventListener('load', resolve);
        });
    }
    /**
     * All JS resources are loaded, but not necessarily processed.
     * We assume no messaging-related modules return any Promise,
     * therefore they should be processed *at most* asynchronously at
     * "Promise time".
     */
    await new Promise(resolve => setTimeout(resolve));
    for (const patch of patches) {
        const definition = registry.get(patch.name);
        if (!definition) {
            throw new Error(`Cannot patch model "${patch.name}": there is no model registered under this name.`);
        }
        patchLifecycleHooks(patch);
        patchModelMethods(patch);
        patchRecordMethods(patch);
        patchFields(patch);
        addOnChanges(patch.name, patch.onChanges);
    }
    patchesAppliedPromise.resolve();
})();
