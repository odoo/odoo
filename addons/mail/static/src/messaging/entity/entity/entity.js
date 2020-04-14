odoo.define('mail.messaging.entity.Entity', function (require) {
'use strict';

const {
    fields: {
        one2one,
    },
    registerNewEntity,
} = require('mail.messaging.entity.core');

const STORED_RELATION_PREFIX = `_`;

function EntityFactory() {

    class Entity {

        //--------------------------------------------------------------------------
        // Public
        //--------------------------------------------------------------------------

        /**
         * Returns all instance entities of this entity class.
         *
         * @static
         * @returns {mail.messaging.entity.Entity[]} all instances of this entity
         */
        static get all() {
            const { state } = this.env.store;
            return Object.values(state.entities).filter(entity => entity instanceof this);
        }

        /**
         * This method is used to create new entity instances of this class
         * with provided data. This is the only way to create them:
         * instantiation must never been done with keyword `new` outside of this
         * function, otherwise the instance entity will not be registered.
         *
         * Provided data is used to update this instance entity for the 1st time.
         * These data should be explicitly handled in `_update()` method,
         * otherwise they are ignored.
         *
         * @static
         * @param {Object} [data={}] data object with initial data, including relations.
         * @returns {mail.messaging.entity.Entity} newly created entity
         */
        static create(data = {}) {
            const { state } = this.env.store;
            const entity = new this(data);
            Object.defineProperty(entity, 'env', {
                get: () => this.env,
            });
            entity.localId = entity._createInstanceLocalId(data);
            this.__init(entity);

            state.entities[entity.localId] = entity;
            // ensure observable version of entity is handled.
            const proxifiedEntity = state.entities[entity.localId];
            proxifiedEntity._update(data);
            return proxifiedEntity;
        }

        /**
         * Get the instance entity that has provided id, if it exists.
         *
         * @static
         * @param {any} id
         * @returns {mail.messaging.entity.Entity|undefined}
         */
        static fromId(id) {
            return this.all.find(entity => entity.id === id);
        }

        /**
         * This method returns the entity of this class that matches provided
         * local id. Useful to convert a local id to an entity. Note that even
         * if there's a entity in the system having provided local id, if the
         * resulting entity is not an instance of this class, this getter
         * assumes the entity does not exist.
         *
         * @static
         * @param {string|mail.messaging.entity.Entity|undefined} entityOrLocalId
         * @returns {mail.messaging.entity.Entity|undefined}
         */
        static get(entityOrLocalId) {
            const { state } = this.env.store;
            if (entityOrLocalId === undefined) {
                return undefined;
            }
            const entity = state.entities[
                entityOrLocalId.isEntity
                    ? entityOrLocalId.localId
                    : entityOrLocalId
            ];
            if (!(entity instanceof this) && entity !== this) {
                return;
            }
            return entity;
        }

        /**
         * This method creates an instance entity or updates one, depending
         * on provided data. This method assumes that instance entities are
         * uniquely identifiable per their `id` data.
         *
         * @static
         * @param {Object} data
         * @param {any} data.id
         * @returns {mail.messaging.entity.Entity} created or updated entity.
         */
        static insert(data) {
            let entity = this.fromId(data.id);
            if (!entity) {
                entity = this.create(data);
            } else {
                entity.update(data);
            }
            return entity;
        }

        /**
         * @static
         * @return {Object[]}
         */
        static get relations() {
            return Object.entries(this.fields)
                .filter(([fieldName, field]) => field.fieldType === 'relation');
        }

        /**
         * This method deletes this instance entity. After this operation, it's
         * as if this entity never existed. Note that relation are removed,
         * which may delete more relations if some of them are causal.
         */
        delete() {
            const { state } = this.env.store;
            if (!this.constructor.get(this)) {
                // Entity has already been deleted.
                // (e.g. unlinking one of its reverse relation was causal)
                return;
            }
            const data = {};
            for (const [relationName, relation] of this.constructor.relations) {
                if (relation.isCausal) {
                    switch (relation.type) {
                        case 'one2one':
                        case 'many2one':
                            if (this[relationName]) {
                                this[relationName].delete();
                            }
                            break;
                        case 'one2many':
                        case 'many2many':
                            for (const relatedEntity of this[relationName]) {
                                relatedEntity.delete();
                            }
                            break;
                    }
                }
                data[relationName] = null;
            }
            this.unlink(data);
            delete state.entities[this.localId];
        }

        /**
         * @returns {boolean}
         */
        get isEntity() {
            return true;
        }

        /**
         * Update relation on this instance entity with provided data.
         *
         * Relations of type x2one are processed as "replacement", while
         * relations of type x2many are processed as as "addition".
         *
         * Key should be named after relation names, and each values should be
         * either local id(s) or entity(ies) that respect the definition of
         * this relation.
         *
         * @param {Object} data
         */
        link(data) {
            for (const [relationName, relationValue] of Object.entries(data)) {
                const relation = this.constructor.fields[relationName];
                switch (relation.type) {
                    case 'one2one':
                        this.constructor.__linkSingleOne2One(this, {
                            relationName,
                            relationValue,
                        });
                        break;
                    case 'one2many':
                        this.constructor.__linkSingleOne2Many(this, {
                            relationName,
                            relationValue,
                        });
                        break;
                    case 'many2one':
                        this.constructor.__linkSingleMany2One(this, {
                            relationName,
                            relationValue,
                        });
                        break;
                    case 'many2many':
                        this.constructor.__linkSingleMany2Many(this, {
                            relationName,
                            relationValue,
                        });
                        break;
                }
            }
        }

        /**
         * Update relation on this instance entity with provided data.
         *
         * Any relation, regardless of their type, are processed as removal
         * of provided value.
         *
         * Key should be named after relation names, and each values should be
         * either local id(s) or entity(ies) that respect the definition of
         * this relation. Special value `null` can be used to remove all
         * relations of provided relation name.
         *
         * @param {Object} data
         */
        unlink(data) {
            if (!this.constructor.get(this)) {
                // Entity has already been deleted.
                // (e.g. unlinking one of its reverse relation was causal)
                return;
            }
            for (const [relationName, relationValue] of Object.entries(data)) {
                const relation = this.constructor.fields[relationName];
                switch (relation.type) {
                    case 'one2one':
                        this.constructor.__unlinkSingleOne2One(this, { relationName });
                        break;
                    case 'one2many':
                        this.constructor.__unlinkSingleOne2Many(this, { relationName, relationValue });
                        break;
                    case 'many2one':
                        this.constructor.__unlinkSingleMany2One(this, { relationName });
                        break;
                    case 'many2many':
                        this.constructor.__unlinkSingleMany2Many(this, { relationName, relationValue });
                        break;
                }
            }
        }

        /**
         * Update this instance entity with provided data.
         *
         * Provided data is used to update this instance entity for the 1st time.
         * These data should be explicitly handled in `_update()` method,
         * otherwise they are ignored.
         *
         * @param {Object} [data={}]
         */
        update(data = {}) {
            this._update(data);
        }

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        /**
         * This method generates a local id for this instance entity that is
         * being created at the moment.
         *
         * This function helps customizing the local id to ease mapping a local
         * id to its entity for the developer that reads the local id. For
         * instance, the local id of a thread cache could combine the thread
         * and stringified domain in its local id, which is much easier to
         * track relations and entities in the system instead of arbitrary
         * number to differenciate them.
         *
         * @private
         * @param {Object} data
         * @returns {string}
         */
        _createInstanceLocalId(data) {
            return _.uniqueId(`${this.constructor.name}_`);
        }

        /**
         * This method is called when this instance entity is being created or
         * updated with provided data. This method should be overriden in order
         * to manage the data, otherwise they are ignored.
         *
         * @abstract
         * @private
         * @param {Object} data
         */
        _update(data) {}

        //--------------------------------------------------------------------------
        // Internal
        //--------------------------------------------------------------------------

        /**
         * Technical management of initialisation of provided entity. Should
         * never be called/overriden outside of this file.
         *
         * @static
         * @private
         * @param {mail.messaging.entity.Entity} entity
         */
        static __init(entity) {
            for (const [relationName, relation] of this.relations) {
                if (['one2many', 'many2many'].includes(relation.type)) {
                    // Ensure X2many relations are arrays by defaults.
                    const storedRelationName = this.__getStoredRelationName(relationName);
                    entity[storedRelationName] = [];
                }
                // compute getters
                Object.defineProperty(entity, relationName, {
                    get: () => {
                        const storedRelationName = this.__getStoredRelationName(relationName);
                        const RelatedEntity = this.env.entities[relation.to];
                        if (['one2one', 'many2one'].includes(relation.type)) {
                            return RelatedEntity.get(entity[storedRelationName]);
                        }
                        return entity[storedRelationName]
                            .map(localId => RelatedEntity.get(localId))
                            /**
                             * FIXME: Stored relation may still contain
                             * outdated entities.
                             */
                            .filter(entity => !!entity);
                    }
                });
            }
        }

        /**
         * This method returns the obj key on this entity that stores data
         * about the relation with provided name. Useful for the technical
         * management of changes in relations, in order to write in the stored
         * key of given entity.
         *
         * Indeed, <entity>.<relationName> is a getter that maps stored data
         * of relation to entities. Stored data of a set relation contain
         * local ids (reason: normalize data in store).
         *
         * @static
         * @private
         * @param {string} relationName
         * @returns {string}
         */
        static __getStoredRelationName(relationName) {
            return `${STORED_RELATION_PREFIX}${relationName}`;
        }

        /**
         * Technical management of updating a link operation of provided
         * relation of type many2many. Should never be called/overriden outside
         * of this file.
         *
         * @static
         * @private
         * @param {mail.messaging.entity.Entity} entity
         * @param {Object} param1
         * @param {string} param1.relationName
         * @param {string|mail.messaging.entity.Entity|<mail.messaging.entity.Entity|string>[]} param1.relationValue
         */
        static __linkSingleMany2Many(entity, { relationName, relationValue }) {
            const relation = this.fields[relationName];
            const storedRelationName = this.__getStoredRelationName(relationName);
            const prevValue = entity[storedRelationName];
            const value = relationValue instanceof Array
                ? relationValue.map(e => e.isEntity ? e.localId: e)
                : [relationValue.isEntity ? relationValue.localId : relationValue];
            if (value.every(valueItem => prevValue.includes(valueItem))) {
                // Do not alter relations if unchanged.
                return;
            }
            entity[storedRelationName] = [...new Set(entity[storedRelationName].concat(value))];
            for (const valueItem of value) {
                if (prevValue.includes(valueItem)) {
                    continue;
                }
                const RelatedEntity = this.env.entities[relation.to];
                const related = RelatedEntity.get(valueItem);
                const storedRelatedRelationName =
                    RelatedEntity.__getStoredRelationName(relation.inverse);
                related[storedRelatedRelationName] = [
                    ...new Set(related[storedRelatedRelationName].concat([entity.localId]))
                ];
            }
        }

        /**
         * Technical management of updating a link operation of provided
         * relation of type many2one. Should never be called/overriden outside
         * of this file.
         *
         * @static
         * @private
         * @param {mail.messaging.entity.Entity} entity
         * @param {Object} param1
         * @param {string} param1.relationName
         * @param {string|mail.messaging.entity.Entity} param1.relationValue
         */
        static __linkSingleMany2One(entity, { relationName, relationValue }) {
            const relation = this.fields[relationName];
            const storedRelationName = this.__getStoredRelationName(relationName);
            const prevValue = entity[storedRelationName];
            const value = relationValue.isEntity ? relationValue.localId : relationValue;
            if (value === entity[storedRelationName]) {
                // Do not alter relations if unchanged.
                return;
            }
            entity[storedRelationName] = value;
            const RelatedEntity = this.env.entities[relation.to];
            if (prevValue) {
                const related = RelatedEntity.get(prevValue);
                if (!related) {
                    // prev Entity has already been deleted.
                    return;
                }
                const storedRelatedRelationName =
                    RelatedEntity.__getStoredRelationName(relation.inverse);
                related[storedRelatedRelationName] =
                    related[storedRelatedRelationName].filter(
                        valueItem => valueItem !== entity.localId
                    );
                if (relation.isCausal) {
                    related.delete();
                }
            }
            const related = RelatedEntity.get(value);
            const storedRelatedRelationName =
                RelatedEntity.__getStoredRelationName(relation.inverse);
            related[storedRelatedRelationName] =
                    related[storedRelatedRelationName].concat([entity.localId]);
        }

        /**
         * Technical management of updating a link operation of provided
         * relation of type one2many. Should never be called/overriden outside
         * of this file.
         *
         * @static
         * @private
         * @param {mail.messaging.entity.Entity} entity
         * @param {Object} param1
         * @param {string} param1.relationName
         * @param {string|mail.messaging.entity.Entity|<string|mail.messaging.entity.Entity>[]} param1.relationValue
         */
        static __linkSingleOne2Many(entity, { relationName, relationValue }) {
            const relation = this.fields[relationName];
            const storedRelationName = this.__getStoredRelationName(relationName);
            const prevValue = entity[storedRelationName];
            const value = relationValue instanceof Array
                ? relationValue.map(e => e.isEntity ? e.localId: e)
                : [relationValue.isEntity ? relationValue.localId : relationValue];
            if (value.every(valueItem => prevValue.includes(valueItem))) {
                // Do not alter relations if unchanged.
                return;
            }
            entity[storedRelationName] = [...new Set(entity[storedRelationName].concat(value))];
            for (const valueItem of value) {
                if (prevValue.includes(valueItem)) {
                    continue;
                }
                const RelatedEntity = this.env.entities[relation.to];
                const related = RelatedEntity.get(valueItem);
                const storedRelatedRelationName =
                    RelatedEntity.__getStoredRelationName(relation.inverse);
                related[storedRelatedRelationName] = entity.localId;
            }
        }

        /**
         * Technical management of updating a link operation of provided
         * relation of type one2one. Should never be called/overriden outside
         * of this file.
         *
         * @static
         * @private
         * @param {mail.messaging.entity.Entity} entity
         * @param {Object} param1
         * @param {string} param1.relationName
         * @param {string|mail.messaging.entity.Entity} param1.relationValue
         */
        static __linkSingleOne2One(entity, { relationName, relationValue }) {
            const relation = this.fields[relationName];
            const storedRelationName = this.__getStoredRelationName(relationName);
            const prevValue = entity[storedRelationName];
            const value = relationValue.isEntity ? relationValue.localId : relationValue;
            entity[storedRelationName] = value;
            const RelatedEntity = this.env.entities[relation.to];
            if (prevValue) {
                const related = RelatedEntity.get(prevValue);
                const storedRelatedRelationName =
                    RelatedEntity.__getStoredRelationName(relation.inverse);
                related[storedRelatedRelationName] = undefined;
                if (relation.isCausal) {
                    related.delete();
                }
            }
            const related = RelatedEntity.get(value);
            const storedRelatedRelationName = RelatedEntity.__getStoredRelationName(relation.inverse);
            related[storedRelatedRelationName] = entity.localId;
        }

        /**
         * Technical management of unlink operation of provided relation of
         * type many2many. Should never be called/overriden outside of this file.
         *
         * @static
         * @private
         * @param {mail.messaging.entity.Entity} entity
         * @param {Object} param1
         * @param {string} param1.relationName
         * @param {string|mail.messaging.entity.Entity|<string|mail.messaging.entity.Entity>[]|null} param1.relationValue
         */
        static __unlinkSingleMany2Many(entity, { relationName, relationValue }) {
            if (!this.get(entity)) {
                // Entity has already been deleted.
                // (e.g. unlinking one of its reverse relation was causal)
                return;
            }
            const relation = this.fields[relationName];
            const storedRelationName = this.__getStoredRelationName(relationName);
            const value = relationValue === null
                ? [...entity[storedRelationName]]
                : relationValue instanceof Array
                ? relationValue.map(e => e.isEntity ? e.localId: e)
                : [relationValue.isEntity ? relationValue.localId : relationValue];
            entity[storedRelationName] = entity[storedRelationName].filter(
                valueItem => !value.includes(valueItem)
            );
            const RelatedEntity = this.env.entities[relation.to];
            for (const valueItem of value) {
                const related = RelatedEntity.get(valueItem);
                const storedRelatedRelationName =
                    RelatedEntity.__getStoredRelationName(relation.inverse);
                related[storedRelatedRelationName] =
                    related[storedRelatedRelationName].filter(
                        valueItem => valueItem !== entity.localId
                    );
                if (relation.isCausal) {
                    related.delete();
                }
            }
        }

        /**
         * Technical management of unlink operation of provided relation of
         * type many2one. Should never be called/overriden outside of this file.
         *
         * @static
         * @private
         * @param {mail.messaging.entity.Entity} entity
         * @param {Object} param1
         * @param {string} param1.relationName
         */
        static __unlinkSingleMany2One(entity, { relationName }) {
            if (!this.get(entity)) {
                // Entity has already been deleted.
                // (e.g. unlinking one of its reverse relation was causal)
                return;
            }
            const relation = this.fields[relationName];
            const storedRelationName = this.__getStoredRelationName(relationName);
            const prevValue = entity[storedRelationName];
            if (prevValue) {
                const RelatedEntity = this.env.entities[relation.to];
                const prevEntity = RelatedEntity.get(prevValue);
                RelatedEntity.__unlinkSingleOne2Many(prevEntity, {
                    relationName: relation.inverse,
                    relationValue: entity.localId,
                });
            }
        }

        /**
         * Technical management of unlink operation of provided relation of
         * type one2many. Should never be called/overriden outside of this file.
         *
         * @static
         * @private
         * @param {string|mail.messaging.entity.Entity} entity
         * @param {Object} param1
         * @param {string} param1.relationName
         * @param {string|mail.messaging.entity.Entity|<string|mail.messaging.entity.Entity>[]|null} param1.relationValue
         *   if null, unlink all items in the relation of provided entity.
         */
        static __unlinkSingleOne2Many(entity, { relationName, relationValue }) {
            if (!this.get(entity)) {
                // Entity has already been deleted.
                // (e.g. unlinking one of its reverse relation was causal)
                return;
            }
            const relation = this.fields[relationName];
            const storedRelationName = this.__getStoredRelationName(relationName);
            const prevValue = entity[storedRelationName];
            const value = relationValue === null
                ? [...entity[storedRelationName]]
                : relationValue instanceof Array
                ? relationValue.map(e => e.isEntity ? e.localId: e)
                : [relationValue.isEntity ? relationValue.localId : relationValue];
            entity[storedRelationName] = entity[storedRelationName].filter(
                valueItem => !value.includes(valueItem)
            );
            if (prevValue) {
                const RelatedEntity = this.env.entities[relation.to];
                for (const valueItem of value) {
                    const related = RelatedEntity.get(valueItem);
                    const storedRelatedRelationName =
                        RelatedEntity.__getStoredRelationName(relation.inverse);
                    related[storedRelatedRelationName] = undefined;
                    if (relation.isCausal) {
                        related.delete();
                    }
                }
            }
        }

        /**
         * Technical management of unlink operation of provided relation of
         * type one2one. Should never be called/overriden outside of this file.
         *
         * @static
         * @private
         * @param {mail.messaging.entity.Entity} entity
         * @param {Object} param1
         * @param {string} param1.relationName
         */
        static __unlinkSingleOne2One(entity, { relationName }) {
            if (!this.get(entity)) {
                // Entity has already been deleted.
                // (e.g. unlinking one of its reverse relation was causal)
                return;
            }
            const relation = this.fields[relationName];
            const storedRelationName = this.__getStoredRelationName(relationName);
            const prevValue = entity[storedRelationName];
            entity[storedRelationName] = undefined;
            const RelatedEntity = this.env.entities[relation.to];
            if (prevValue) {
                const related = RelatedEntity.get(prevValue);
                const storedRelatedRelationName =
                    RelatedEntity.__getStoredRelationName(relation.inverse);
                related[storedRelatedRelationName] = undefined;
            }
        }

    }

    Object.assign(Entity, {
        /**
         * Schema of relations for this entity.
         *
         * Format:
         *
         *   <relation-name>:
         *      {
         *         inverse: Name of inverse relation on related entity.
         *         isCausal: boolean that determines whether the related entities
         *                   are deeply connected to existence of current entity.
         *                   (default: false)
         *         to: Name of the related entity. Just for documentation sake.
         *         type: Type of the relation on this entity.
         *               Either 'one2one', 'one2many', 'many2one' or 'many2many'.
         *      }
         */
        fields: {
            /**
             * Related dialog of entity when dialog content is directly linked to
             * an entity that models a UI component, such as AttachmentViewer. Such
             * entities must be created from @see `mail.messaging.entity.DialogManager.open()`
             */
            dialog: one2one('Dialog', {
                inverse: 'entity',
                isCausal: true,
            }),
        },
    });

    return Entity;
}

registerNewEntity('Entity', EntityFactory);

});
