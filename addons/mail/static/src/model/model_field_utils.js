odoo.define('mail/static/src/model/model_field_utils.js', function (require) {
'use strict';

//------------------------------------------------------------------------------
// Private
//------------------------------------------------------------------------------

/**
 * @private
 * @param {string} modelName
 * @param {Object} [options]
 */
function _relation(modelName, options) {
    return Object.assign({
        fieldType: 'relation',
        to: modelName,
    }, options);
}

//------------------------------------------------------------------------------
// Public
//------------------------------------------------------------------------------

/**
 * Define an attribute field.
 *
 * @param {Object} [options]
 * @returns {Object}
 */
function attr(options) {
    return Object.assign({ fieldType: 'attribute' }, options);
}

/**
 * Define a many2many field.
 *
 * @param {string} modelName
 * @param {Object} [options]
 * @returns {Object}
 */
function many2many(modelName, options) {
    return _relation(modelName, Object.assign({}, options, { relationType: 'many2many' }));
}

/**
 * Define a many2one field.
 *
 * @param {string} modelName
 * @param {Object} [options]
 * @returns {Object}
 */
function many2one(modelName, options) {
    return _relation(modelName, Object.assign({}, options, { relationType: 'many2one' }));
}

/**
 * Define a one2many field.
 *
 * @param {string} modelName
 * @param {Object} [options]
 * @returns {Object}
 */
function one2many(modelName, options) {
    return _relation(modelName, Object.assign({}, options, { relationType: 'one2many' }));
}

/**
 * Define a one2one field.
 *
 * @param {string} modelName
 * @param {Object} [options]
 * @returns {Object}
 */
function one2one(modelName, options) {
    return _relation(modelName, Object.assign({}, options, { relationType: 'one2one' }));
}

return {
    attr,
    many2many,
    many2one,
    one2many,
    one2one,
};

});
