/** @odoo-module **/

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
export function addFields(modelName, fields) {
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
export function addLifecycleHooks(modelName, hooks) {
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
export function addModelGetters(modelName, modelGetters) {
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
export function addModelMethods(modelName, modelMethods) {
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
 * @param {OnChange[]} onChanges Array of onChanges to be added.
 */
export function addOnChanges(modelName, onChanges) {
    if (!registry.has(modelName)) {
        throw new Error(`Cannot add onChanges to model "${modelName}": model must be registered before onChanges can be added.`);
    }
    registry.get(modelName).get('onChanges').push(...onChanges);
}

/**
 * Adds the provided record methods to the model specified by the `modelName`.
 *
 * @param {string} modelName The name of the model to which to add the methods.
 * @param {Object} recordMethods Record methods to be added. key = name, value = method
 */
export function addRecordMethods(modelName, recordMethods) {
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
export function addRecordGetters(modelName, recordGetters) {
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
    const validHookNames = new Set(['_created', '_willDelete']);
    if (!validHookNames.has(name)) {
        throw new Error("invalid hook name.");
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
 * Asserts that the provided `key` has already been defined within the section
 * `sectionName` on the model `modelDefinition`.
 *
 * @param {string} sectionName The section of the `modelDefinition` to check into.
 * @param {string} key The key to check for.
 * @param {Object} modelDefinition The definition of the model to check.
 */
function assertSectionHasKey(sectionName, key, modelDefinition) {
    if (!modelDefinition.get(sectionName).has(key)) {
        throw new Error(`"${key}" is not defined yet on "${sectionName}".`);
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

/**
 * Overrides the lifecycle hooks of the model specified by the `modelName`.
 *
 * @param {string} modelName The name of the model to which to apply the patch.
 * @param {Object} hooks Lifecycle hooks to be overriden. key = name, value = handler
 */
export function patchLifecycleHooks(modelName, hooks) {
    if (!registry.has(modelName)) {
        throw new Error(`Cannot patch lifecycle hooks on model "${modelName}": model must be registered before being patched.`);
    }
    const definition = registry.get(modelName);
    for (const [name, handler] of Object.entries(hooks)) {
        addContextToErrors(() => {
            assertIsFunction(handler);
            assertIsValidHookName(name);
            assertSectionHasKey('lifecycleHooks', name, definition);
        }, `Cannot patch lifecycle hook "${name}" on model "${modelName}": `);
        const hookBeforePatch = definition.get('lifecycleHooks').get(name);
        definition.get('lifecycleHooks').set(name, function (...args) {
            this._super = hookBeforePatch;
            return handler.call(this, ...args);
        });
    }
}

/**
 * Overrides the model methods of the model specified by the `modelName`.
 *
 * @param {string} modelName The name of the model to which to apply the patch.
 * @param {Object} methods Model methods to be overriden. key = name, value = method
 */
export function patchModelMethods(modelName, modelMethods) {
    if (!registry.has(modelName)) {
        throw new Error(`Cannot patch model methods on model "${modelName}": model must be registered before being patched.`);
    }
    const definition = registry.get(modelName);
    for (const [name, method] of Object.entries(modelMethods)) {
        addContextToErrors(() => {
            assertIsFunction(method);
            assertSectionHasKey('modelMethods', name, definition);
        }, `Cannot patch model method "${name}" on model "${modelName}": `);
        const methodBeforePatch = definition.get('modelMethods').get(name);
        definition.get('modelMethods').set(name, function (...args) {
            this._super = methodBeforePatch;
            return method.call(this, ...args);
        });
    }
}

/**
 * Overrides the record methods of the model specified by the `modelName`.
 *
 * @param {string} modelName The name of the model to which to apply the patch.
 * @param {Object} methods Record methods to be overriden. key = name, value = method
 */
export function patchRecordMethods(modelName, recordMethods) {
    if (!registry.has(modelName)) {
        throw new Error(`Cannot patch record methods on model "${modelName}": model must be registered before being patched.`);
    }
    const definition = registry.get(modelName);
    for (const [name, method] of Object.entries(recordMethods)) {
        addContextToErrors(() => {
            assertIsFunction(method);
            assertSectionHasKey('recordMethods', name, definition);
        }, `Cannot patch record method "${name}" on model "${modelName}": `);
        const methodBeforePatch = definition.get('recordMethods').get(name);
        definition.get('recordMethods').set(name, function (...args) {
            this._super = methodBeforePatch;
            return method.call(this, ...args);
        });
    }
}

/**
 * @param {Object} definition The JSON definition of the model to register.
 * @param {Object} [definition.fields]
 * @param {string} [definition.identifyingMode='and']
 * @param {Object} [definition.lifecycleHooks]
 * @param {Object} [definition.modelGetters] Deprecated; use fields instead.
 * @param {Object} [definition.modelMethods]
 * @param {string} definition.name
 * @param {OnChanges[]} [definition.onChanges]
 * @param {Object} [definition.recordGetters] Deprecated; use fields instead.
 * @param {Object} [definition.recordMethods]
 */
export function registerModel({ fields, identifyingMode = 'and', lifecycleHooks, modelGetters, modelMethods, name, onChanges, recordGetters, recordMethods }) {
    if (!name) {
        throw new Error("Model is lacking a name.");
    }
    if (!identifyingMode) {
        throw new Error(`Cannot register model "${name}": definition is lacking identifying mode.`);
    }
    if (registry.has(name)) {
        throw new Error(`Cannot register model "${name}": model has already been registered.`);
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
