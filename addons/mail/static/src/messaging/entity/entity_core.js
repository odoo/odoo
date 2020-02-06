odoo.define('mail.messaging.entity.core', function (require) {
'use strict';

const { patchClassMethods, patchInstanceMethods } = require('mail.messaging.utils');

const registry = {};

//------------------------------------------------------------------------------
// Private
//------------------------------------------------------------------------------

/**
 * @private
 * @param {string} entityName
 * @returns {Object}
 */
function _getEntryFromEntityName(entityName) {
    if (!registry[entityName]) {
        registry[entityName] = {
            dependencies: [],
            factory: undefined,
            name: entityName,
            patches: [],
        };
    }
    return registry[entityName];
}

/**
 * @private
 * @param {string} entityName
 * @param {string} patchName
 * @param {Object} patch
 * @param {Object} [param3={}]
 * @param {string} [param3.type='instance'] 'instance', 'class' or 'relation'
 */
function _registerPatchEntity(entityName, patchName, patch, { type = 'instance' } = {}) {
    const entry = _getEntryFromEntityName(entityName);
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
 * @param {Object} Entities
 * @throws {Error} in case some relations are not correct
 */
function checkRelations(Entities) {
    for (const Entity of Object.values(Entities)) {
        for (const relationName in Entity.relations) {
            const relation = Entity.relations[relationName];
            if (!relation.type) {
                throw new Error(
                    `Relation "${Entity.name}/${relationName}" must define a type in "type".`
                );
            }
            if (!(['one2one', 'one2many', 'many2one', 'many2many'].includes(relation.type))) {
                throw new Error(
                    `Relation "${Entity.name}/${relationName}" has invalid type "${relation.type}".`
                );
            }
            if (!relation.inverse) {
                throw new Error(
                    `Relation "${
                        Entity.name
                    }/${
                        relationName
                    }" must define an inverse relation name in "inverse".`
                );
            }
            if (!relation.to) {
                throw new Error(
                    `Relation "${
                        Entity.name
                    }/${
                        relationName
                    }" must define an Entity class name in "to".`
                );
            }
            const RelatedEntity = Entities[relation.to];
            if (!RelatedEntity) {
                throw new Error(
                    `Entity class name of relation "${Entity.name}/${relationName}" does not exist.`
                );
            }
            const inverseRelation = RelatedEntity.relations[relation.inverse];
            if (!inverseRelation) {
                throw new Error(
                    `Relation entity class "${
                        Entity.name
                    }/${
                        relationName
                    }" has no inverse relation "${RelatedEntity.name}/${relation.inverse}".`
                );
            }
            const allSelfAndParentNames = [];
            let target = Entity;
            while (target) {
                allSelfAndParentNames.push(target.name);
                target = target.__proto__;
            }
            if (!allSelfAndParentNames.includes(inverseRelation.to)) {
                throw new Error(
                    `Relation "${
                        Entity.name
                    }/${
                        relationName
                    }" has inverse relation "${
                        RelatedEntity.name
                    }/${
                        relation.inverse
                    }" misconfigured (currently "${
                        inverseRelation.to
                    }", should instead refer to this entity or parented entity: ${
                        allSelfAndParentNames.map(name => `"${name}"`).join(', ')
                    }?)`
                );
            }
            if (
                (relation.type === 'many2many' && inverseRelation.type !== 'many2many') ||
                (relation.type === 'one2one' && inverseRelation.type !== 'one2one') ||
                (relation.type === 'one2many' && inverseRelation.type !== 'many2one') ||
                (relation.type === 'many2one' && inverseRelation.type !== 'one2many')
            ) {
                throw new Error(
                    `Mismatch relations types "${
                        Entity.name
                    }/${
                        relationName
                    }" (${
                        relation.type
                    }) and "${
                        RelatedEntity.name
                    }/${
                        relation.inverse
                    }" (${
                        inverseRelation.type
                    }).`
                );
            }
        }
    }
}

/**
 * @returns {Object}
 */
function generateEntities() {
    const allNames = Object.keys(registry);
    const Entities = {};
    const generatedNames = [];
    let toGenerateNames = [...allNames];
    while (toGenerateNames.length > 0) {
        const generatable = toGenerateNames.map(name => registry[name]).find(entry => {
            let isGenerateable = true;
            for (const dependencyName of entry.dependencies) {
                if (!generatedNames.includes(dependencyName)) {
                    isGenerateable = false;
                }
            }
            return isGenerateable;
        });
        if (!generatable) {
            throw new Error(`Cannot generate following Entity classes: ${toGenerateNames.split(', ')}`);
        }
        const Entity = generatable.factory(Entities);
        for (const patch of generatable.patches) {
            switch (patch.type) {
                case 'class':
                    patchClassMethods(Entity, patch.name, patch.patch);
                    break;
                case 'instance':
                    patchInstanceMethods(Entity, patch.name, patch.patch);
                    break;
                case 'relation':
                    Object.assign(Entity.relations, patch.patch);
                    break;
            }
        }
        Entities[Entity.name] = Entity;
        generatedNames.push(Entity.name);
        toGenerateNames = toGenerateNames.filter(name => name !== Entity.name);
    }
    return Entities;
}

/**
 *
 * @param {string} entityName
 * @param {string} patchName
 * @param {Object} patch
 */
function registerClassPatchEntity(entityName, patchName, patch) {
    _registerPatchEntity(entityName, patchName, patch, { type: 'class' });
}

/**
 * FIXME: instance patch are not supported due to patch making changes on
 * entity property `_super` each time such a patched method is called, thus
 * incrementing rev number and results in infinite loops.
 * Work-around is to patch class methods, since classes are not observed due
 * to them being functions (and functions are not observed).
 *
 * @param {string} entityName
 * @param {string} patchName
 * @param {Object} patch
 */
function registerInstancePatchEntity(entityName, patchName, patch) {
    throw new Error(`Cannot apply instance entity patch "${
        patchName
    }": Instance patches on entities are not supported. Use class patch instead.`);
    // _registerPatchEntity(entityName, patchName, patch, { isOnClass: false });
}

/**
 * @param {string} name
 * @param {function} factory
 * @param {string[]} [dependencies=[]]
 */
function registerNewEntity(name, factory, dependencies = []) {
    const entry = _getEntryFromEntityName(name);
    let entryDependencies = [...dependencies];
    if (name !== 'Entity') {
        entryDependencies = [...new Set(entryDependencies.concat(['Entity']))];
    }
    if (entry.factory) {
        throw new Error(`Entity class "${name}" has already been registered!`);
    }
    Object.assign(entry, {
        dependencies: entryDependencies,
        factory,
        name,
    });
}


/**
 *
 * @param {string} entityName
 * @param {string} patchName
 * @param {Object} patch
 */
function registerRelationPatchEntity(entityName, patchName, patch) {
    _registerPatchEntity(entityName, patchName, patch, { type: 'relation' });
}

//------------------------------------------------------------------------------
// Export
//------------------------------------------------------------------------------

return {
    checkRelations,
    generateEntities,
    registerClassPatchEntity,
    registerInstancePatchEntity,
    registerNewEntity,
    registerRelationPatchEntity,
};

});
