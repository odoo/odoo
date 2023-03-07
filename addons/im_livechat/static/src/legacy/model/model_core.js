/** @odoo-module **/

import { makeDeferred } from "@im_livechat/legacy/utils/deferred";

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
 * Adds the provided `componentSetup` to the model specified by the `modelName`.
 *
 * @param {string} modelName The name of the model to which to add the
 * componentSetup function.
 * @param {Function} componentSetup The componentSetup function to be added.
 */
function addComponentSetup(modelName, componentSetup) {
    if (typeof componentSetup !== "function") {
        throw new Error(
            `Cannot add componentSetup to model ${modelName}: componentSetup must be a function (current type: "${typeof componentSetup}").`
        );
    }
    registry.get(modelName).set("componentSetup", componentSetup);
}

/**
 * Adds the provided fields to the model specified by the `modelName`.
 *
 * @param {string} modelName The name of the model to which to add the fields.
 * @param {Object} fields Fields to be added. key = field name, value = field attributes
 */
function addFields(modelName, fields) {
    const definition = registry.get(modelName);
    for (const [fieldName, field] of Object.entries(fields)) {
        addContextToErrors(() => {
            assertNameIsAvailableOnRecords(fieldName, definition);
        }, `Cannot add field "${fieldName}" to model "${modelName}": `);
        definition.get("fields").set(fieldName, field);
    }
}

const validHookNames = ["_created", "_willDelete"];

/**
 * Adds the provided hooks to the model specified by the `modelName`.
 *
 * @param {string} modelName The name of the model to which to add the hooks.
 * @param {Object} hooks Hooks to be added. key = name, value = handler
 */
function addLifecycleHooks(modelName, hooks) {
    const definition = registry.get(modelName);
    for (const [name, handler] of Object.entries(hooks)) {
        addContextToErrors(() => {
            assertIsFunction(handler);
            if (!validHookNames.includes(name)) {
                throw new Error(
                    `unsupported hook name. Possible values: ${validHookNames.join(", ")}.`
                );
            }
        }, `Cannot add lifecycle hook "${name}" to model "${modelName}": `);
        definition.get("lifecycleHooks").set(name, handler);
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
    const definition = registry.get(modelName);
    for (const [getterName, getter] of Object.entries(modelGetters)) {
        addContextToErrors(() => {
            assertIsFunction(getter);
            assertNameIsAvailableOnModel(getterName, definition);
        }, `Cannot add model getter "${getterName}" to model "${modelName}": `);
        definition.get("modelGetters").set(getterName, getter);
    }
}

/**
 * Adds the provided model methods to the model specified by the `modelName`.
 *
 * @param {string} modelName The name of the model to which to add the model methods.
 * @param {Object} modelMethods Model methods to be added. key = name, value = method
 */
function addModelMethods(modelName, modelMethods) {
    const definition = registry.get(modelName);
    for (const [name, method] of Object.entries(modelMethods)) {
        addContextToErrors(() => {
            assertIsFunction(method);
            assertNameIsAvailableOnModel(name, definition);
        }, `Cannot add model method "${name}" to model "${modelName}": `);
        definition.get("modelMethods").set(name, method);
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
        for (const onChange of onChanges) {
            if (!Object.prototype.hasOwnProperty.call(onChange, "dependencies")) {
                throw new Error(
                    "at least one onChange definition lacks dependencies (the list of fields to be watched for changes)."
                );
            }
            if (!Object.prototype.hasOwnProperty.call(onChange, "methodName")) {
                throw new Error(
                    "at least one onChange definition lacks a methodName (the name of the method to be called on change)."
                );
            }
            if (!Array.isArray(onChange.dependencies)) {
                throw new Error("onChange dependencies must be an array of strings.");
            }
            if (typeof onChange.methodName !== "string") {
                throw new Error("onChange methodName must be a string.");
            }
            const allowedKeys = ["dependencies", "methodName"];
            for (const key of Object.keys(onChange)) {
                if (!allowedKeys.includes(key)) {
                    throw new Error(
                        `unknown key "${key}" in onChange definition. Allowed keys: ${allowedKeys.join(
                            ", "
                        )}.`
                    );
                }
            }
            // paths of dependencies are splitted now to avoid having to do it
            // each time the path is followed.
            const splittedDependencies = [];
            for (const dependency of onChange.dependencies) {
                if (typeof dependency !== "string") {
                    throw new Error("onChange dependencies must be an array of strings.");
                }
                splittedDependencies.push(dependency.split("."));
            }
            onChange.dependencies = splittedDependencies;
        }
    }, `Cannot add onChanges to model "${modelName}": `);
    registry
        .get(modelName)
        .get("onChanges")
        .push(...onChanges);
}

/**
 * Adds the provided record methods to the model specified by the `modelName`.
 *
 * @param {string} modelName The name of the model to which to add the methods.
 * @param {Object} recordMethods Record methods to be added. key = name, value = method
 */
function addRecordMethods(modelName, recordMethods) {
    const definition = registry.get(modelName);
    for (const [name, method] of Object.entries(recordMethods)) {
        addContextToErrors(() => {
            assertIsFunction(method);
            assertNameIsAvailableOnRecords(name, definition);
        }, `Cannot add record method "${name}" to model "${modelName}": `);
        definition.get("recordMethods").set(name, method);
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
    const definition = registry.get(modelName);
    for (const [getterName, getter] of Object.entries(recordGetters)) {
        addContextToErrors(() => {
            assertIsFunction(getter);
            assertNameIsAvailableOnRecords(getterName, definition);
        }, `Cannot add record getter "${getterName}" to model "${modelName}": `);
        definition.get("recordGetters").set(getterName, getter);
    }
}

/**
 * Asserts that `toAssert` is typeof function.
 *
 * @param {any} toAssert
 * @throws {Error} when `toAssert` is not typeof function.
 */
function assertIsFunction(toAssert) {
    if (typeof toAssert !== "function") {
        throw new Error(`"${toAssert}" must be a function`);
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
    if (["modelGetters", "modelMethods"].some((x) => modelDefinition.get(x).has(name))) {
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
    if (
        ["fields", "recordGetters", "recordMethods"].some((x) => modelDefinition.get(x).has(name))
    ) {
        throw new Error(`there is already a key with this name on the records.`);
    }
}

function patchComponentSetup({ name, componentSetup }) {
    const originalComponentSetup = registry.get(name).get("componentSetup");
    if (!originalComponentSetup) {
        addComponentSetup(name, componentSetup);
        return;
    }
    if (typeof componentSetup !== "function") {
        throw new Error(
            `Cannot patch componentSetup of model ${name}: componentSetup must be a function (current type: "${typeof componentSetup}").`
        );
    }
    registry.get(name).set("componentSetup", function () {
        this._super = originalComponentSetup;
        return componentSetup.call(this);
    });
}

function patchFields(patch) {
    const newFieldsToAdd = Object.create(null);
    for (const [fieldName, fieldData] of Object.entries(patch.fields)) {
        const originalFieldDefinition = registry.get(patch.name).get("fields").get(fieldName);
        if (!originalFieldDefinition) {
            newFieldsToAdd[fieldName] = fieldData;
        } else {
            for (const [attributeName, attributeData] of Object.entries(fieldData)) {
                switch (attributeName) {
                    case "compute": {
                        if (!originalFieldDefinition.compute) {
                            throw new Error(
                                `Cannot patch compute of field ${patch.name}/${fieldName}: the field is not a compute in the original definition.`
                            );
                        }
                        if (typeof attributeData !== "function") {
                            throw new Error(
                                `Cannot patch compute of field ${
                                    patch.name
                                }/${fieldName}: the compute must be a function (found: "${typeof attributeData}").`
                            );
                        }
                        const computeBeforePatch = originalFieldDefinition.compute;
                        originalFieldDefinition.compute = function () {
                            this._super = computeBeforePatch;
                            return attributeData.call(this);
                        };
                        break;
                    }
                    case "sort":
                        if (originalFieldDefinition.sort) {
                            if (typeof attributeData !== "function") {
                                throw new Error(
                                    `Cannot patch sorting rules of field ${
                                        patch.name
                                    }/${fieldName}: the value of 'sort' must be a function to apply to the sorting rules array (found: "${typeof attributeData}").`
                                );
                            }
                            originalFieldDefinition.sort = attributeData.call({
                                _super: originalFieldDefinition.sort,
                            });
                        } else {
                            if (!Array.isArray(attributeData)) {
                                throw new Error(
                                    `Cannot add sorting rules to field ${patch.name}/${fieldName}: sorting rules must be an array.`
                                );
                            }
                            originalFieldDefinition.sort = attributeData;
                        }
                        break;
                    case "fieldType":
                        throw new Error(
                            `Cannot patch field ${patch.name}/${fieldName}: patches do not need field type (attr, one, many).`
                        );
                    default:
                        throw new Error(
                            `Cannot patch field ${patch.name}/${fieldName}: unsupported field attribute "${attributeName}".`
                        );
                }
            }
        }
    }
    addFields(patch.name, newFieldsToAdd);
}

function patchLifecycleHooks(patch) {
    const originalLifecycleHooksDefinition = registry.get(patch.name).get("lifecycleHooks");
    const newLifecycleHooksToAdd = Object.create(null);
    for (const [hookName, hookHandler] of Object.entries(patch.lifecycleHooks)) {
        if (!originalLifecycleHooksDefinition.has(hookName)) {
            newLifecycleHooksToAdd[hookName] = hookHandler;
        } else {
            if (typeof hookHandler !== "function") {
                throw new Error(
                    `Cannot patch hook "${hookName}" on model ${
                        patch.name
                    }: the hook handler must be a function (current type: "${typeof hookHandler}").`
                );
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
    const originalModelMethodsDefinition = registry.get(patch.name).get("modelMethods");
    const newModelMethodsToAdd = Object.create(null);
    for (const [methodName, method] of Object.entries(patch.modelMethods)) {
        if (!originalModelMethodsDefinition.has(methodName)) {
            newModelMethodsToAdd[methodName] = method;
        } else {
            if (typeof method !== "function") {
                throw new Error(
                    `Cannot patch model method "${methodName}" on model ${
                        patch.name
                    }: the method must be a function (current type: "${typeof method}").`
                );
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
    const originalRecordMethods = registry.get(patch.name).get("recordMethods");
    const newRecordMethodsToAdd = Object.create(null);
    for (const [methodName, method] of Object.entries(patch.recordMethods)) {
        if (!originalRecordMethods.has(methodName)) {
            newRecordMethodsToAdd[methodName] = method;
        } else {
            if (typeof method !== "function") {
                throw new Error(
                    `Cannot patch record method "${methodName}" on model ${
                        patch.name
                    }: the method must be a function (current type: "${typeof method}").`
                );
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
 * @param {function} [definition.componentSetup]
 * @param {Object} [definition.fields]
 * @param {string} [definition.identifyingMode='and']
 * @param {string} [definition.isLegacyComponent=false]
 * @param {Object} [definition.lifecycleHooks]
 * @param {Object} [definition.modelGetters] Deprecated; use fields instead.
 * @param {Object} [definition.modelMethods]
 * @param {string} definition.name
 * @param {Object[]} [definition.onChanges]
 * @param {Object} [definition.recordGetters] Deprecated; use fields instead.
 * @param {Object} [definition.recordMethods]
 * @param {string} [definition.template]
 */
export function Model({
    componentSetup,
    fields,
    identifyingMode = "and",
    isLegacyComponent = false,
    lifecycleHooks,
    modelGetters,
    modelMethods,
    name,
    onChanges,
    recordGetters,
    recordMethods,
    template,
}) {
    if (!name) {
        throw new Error("Model is lacking a name.");
    }
    if (registry.has(name)) {
        throw new Error(`Cannot register model "${name}": model has already been registered.`);
    }
    const sectionNames = [
        "name",
        "template",
        "componentSetup",
        "identifyingMode",
        "isLegacyComponent",
        "lifecycleHooks",
        "modelMethods",
        "modelGetters",
        "recordMethods",
        "recordGetters",
        "fields",
        "onChanges",
    ];
    const invalidSectionNames = Object.keys(arguments[0]).filter((x) => !sectionNames.includes(x));
    if (invalidSectionNames.length > 0) {
        throw new Error(
            `Cannot register model "${name}": model definition contains unknown key(s): ${invalidSectionNames.join(
                ", "
            )}`
        );
    }
    registry.set(
        name,
        new Map([
            ["name", name],
            ["identifyingMode", identifyingMode],
            ["isLegacyComponent", isLegacyComponent],
            ["lifecycleHooks", new Map()],
            ["modelMethods", new Map()],
            ["modelGetters", new Map()],
            ["recordMethods", new Map()],
            ["recordGetters", new Map()],
            ["fields", new Map()],
            ["onChanges", []],
        ])
    );
    if (template) {
        registry.get(name).set("template", template);
        if (componentSetup) {
            addComponentSetup(name, componentSetup);
        }
    }
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

export function Patch({
    componentSetup,
    fields,
    lifecycleHooks,
    modelMethods,
    name,
    onChanges,
    recordMethods,
}) {
    if (!name) {
        throw new Error("Patch is lacking the name of the model to be patched.");
    }
    const allowedSectionNames = [
        "name",
        "componentSetup",
        "lifecycleHooks",
        "modelMethods",
        "recordMethods",
        "fields",
        "onChanges",
    ];
    const invalidSectionNames = Object.keys(arguments["0"]).filter(
        (x) => !allowedSectionNames.includes(x)
    );
    if (invalidSectionNames.length > 0) {
        throw new Error(
            `Error while registering patch for model "${name}": patch definition contains unsupported key(s): ${invalidSectionNames.join(
                ", "
            )}`
        );
    }
    patches.push({
        name,
        componentSetup: componentSetup || undefined,
        lifecycleHooks: lifecycleHooks || {},
        modelMethods: modelMethods || {},
        recordMethods: recordMethods || {},
        fields: fields || {},
        onChanges: onChanges || [],
    });
}

export const patchesAppliedPromise = makeDeferred();

(async function applyPatches() {
    if (document.readyState !== "complete") {
        await new Promise((resolve) => {
            /**
             * Called when all JS resources are loaded. This is useful to
             * ensure all definitions have been parsed before applying patches.
             */
            window.addEventListener("load", resolve);
        });
    }
    /**
     * All JS resources are loaded, but not necessarily processed.
     * We assume no messaging-related modules return any Promise,
     * therefore they should be processed *at most* asynchronously at
     * "Promise time".
     */
    await new Promise((resolve) => setTimeout(resolve));
    for (const patch of patches) {
        const definition = registry.get(patch.name);
        if (!definition) {
            throw new Error(
                `Cannot patch model "${patch.name}": there is no model registered under this name.`
            );
        }
        if (patch.componentSetup) {
            patchComponentSetup(patch);
        }
        patchLifecycleHooks(patch);
        patchModelMethods(patch);
        patchRecordMethods(patch);
        patchFields(patch);
        addOnChanges(patch.name, patch.onChanges);
    }
    patchesAppliedPromise.resolve();
})();
