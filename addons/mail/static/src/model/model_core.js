odoo.define('mail/static/src/model/model_core.js', function (require) {
'use strict';

/**
 * Module that contains registry for adding new models or patching models.
 * Useful for model manager in order to generate model classes.
 *
 * This code is not in model manager because other JS modules should populate
 * a registry, and it's difficult to ensure availability of the model manager
 * when these JS modules are deployed.
 */

const registry = {};

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
function registerNewModel(name, factory, dependencies = []) {
    const entry = _getEntryFromModelName(name);
    let entryDependencies = [...dependencies];
    if (name !== 'mail.model') {
        entryDependencies = [...new Set(entryDependencies.concat(['mail.model']))];
    }
    if (entry.factory) {
        throw new Error(`Model "${name}" has already been registered!`);
    }
    Object.assign(entry, {
        dependencies: entryDependencies,
        factory,
        name,
    });
}

//------------------------------------------------------------------------------
// Export
//------------------------------------------------------------------------------

return {
    registerClassPatchModel,
    registerFieldPatchModel,
    registerInstancePatchModel,
    registerNewModel,
    registry,
};

});
