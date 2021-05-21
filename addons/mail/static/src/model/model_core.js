/** @odoo-module **/

/**
 * Module that contains registry for adding new models or patching models.
 * Useful for model manager in order to generate model classes.
 *
 * This code is not in model manager because other JS modules should populate
 * a registry, and it's difficult to ensure availability of the model manager
 * when these JS modules are deployed.
 */

const registry = {};

// TODO SEB need to get rid of this file

//------------------------------------------------------------------------------
// Private
//------------------------------------------------------------------------------

/**
 * @private
 * @param {string} modelName
 * @returns {Object}
 */
function _getEntryFromModelName(modelName) {
    if (!registry[modelName]) {
        registry[modelName] = {
            dependencies: [],
            factory: undefined,
            name: modelName,
            patches: [],
        };
    }
    return registry[modelName];
}

/**
 * @private
 * @param {string} modelName
 * @param {string} patchName
 * @param {Object} patch
 * @param {Object} [param3={}]
 * @param {string} [param3.type='instance'] 'instance', 'class' or 'field'
 */
function _registerPatchModel(modelName, patchName, patch, { type = 'instance' } = {}) {
    const entry = _getEntryFromModelName(modelName);
    Object.assign(entry, {
        patches: (entry.patches || []).concat([{
            name: patchName,
            patch,
            type,
        }]),
    });
}

//------------------------------------------------------------------------------
// Public
//------------------------------------------------------------------------------

/**
 * Register a patch for static methods in model.
 *
 * @param {string} modelName
 * @param {string} patchName
 * @param {Object} patch
 */
function registerClassPatchModel(modelName, patchName, patch) {
    _registerPatchModel(modelName, patchName, patch, { type: 'class' });
}

/**
 * Register a patch for fields in model.
 *
 * @param {string} modelName
 * @param {string} patchName
 * @param {Object} patch
 */
function registerFieldPatchModel(modelName, patchName, patch) {
    _registerPatchModel(modelName, patchName, patch, { type: 'field' });
}

/**
 * Register a patch for instance methods in model.
 *
 * @param {string} modelName
 * @param {string} patchName
 * @param {Object} patch
 */
function registerInstancePatchModel(modelName, patchName, patch) {
    _registerPatchModel(modelName, patchName, patch, { type: 'instance' });
}

/**
 * @param {string} name
 * @param {function} factory
 * @param {string[]} [dependencies=[]]
 */
function registerNewModel(name, factory) {
    const entry = _getEntryFromModelName(name);
    const dependencies = (name !== 'mail.model') ? ['mail.model'] : [];
    Object.assign(entry, {
        dependencies,
        factory,
        name,
    });
}

//------------------------------------------------------------------------------
// Export
//------------------------------------------------------------------------------

export {
    registerClassPatchModel,
    registerFieldPatchModel,
    registerInstancePatchModel,
    registerNewModel,
    registry,
};

