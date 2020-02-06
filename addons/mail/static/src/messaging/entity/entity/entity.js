odoo.define('mail.messaging.entity.Entity', function (require) {
'use strict';

const { registerNewEntity } = require('mail.messaging.entity.core');

const STORED_RELATION_PREFIX = `_`;

function EntityFactory() {

    class Entity {

        /**
         * This method initializes this entity class. This is called on all
         * registered entity classes, and ensure that data, relations, and env
         * are correctly set up before messaging becomes initialized.
         *
         * Provided data is used to update this class entity for the 1st time.
         * These data should be explicitly handled in `static _update()` method,
         * otherwise they are ignored.
         *
         * @static
         * @param {Object} [data]
         */
        static init(data) {
            const { state } = this.env.store;
            this.localId = this.name;
            state.entities[this.localId] = this;
            /**
             * Classes are functions, and changes in functions are not observed
             * by OWL. The work-around is to store data and relations of classes
             * in an object, and make this object observed from store state.
             */
            state.__classEntityObservables[this.localId] = {};
            this.observable = state.__classEntityObservables[this.localId];

            // Class stored relation access (redirect to observable)
            for (const relationName in this.relations) {
                Object.defineProperty(this, this.__getStoredRelationName(relationName), {
                    get: () => this.observable[this.__getStoredRelationName(relationName)],
                });
            }

            // Class attribute access (redirect to observable)
            const classAttributeNames = this._getListOfClassAttributeNames();
            for (const classAttributeName of classAttributeNames) {
                Object.defineProperty(this, classAttributeName, {
                    get: () => this.observable[classAttributeName],
                });
            }

            this.__init(this);
            this.__update(this, data);
        }

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
         * @param {Object} data data object with initial data, including relations.
         * @returns {mail.messaging.entity.Entity} newly created entity
         */
        static create(data) {
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
            this.__update(proxifiedEntity, data);
            return proxifiedEntity;
        }

        /**
         * This method deletes this class entity. After this operation, it's
         * as if this entity never existed. Note that relation are removed,
         * which may delete more relations if some of them are causal.
         *
         * @static
         */
        static delete() {
            for (const entity of this.all) {
                entity.delete();
            }
            this.__delete(this);
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
         * resulting entity is not this class or an instance of this class,
         * this getter assumes the entity does not exist.
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
         * Update relation on this class entity with provided data.
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
        static link(data) {
            this.__link(this, data);
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
         * @returns {boolean}
         */
        static get isEntity() {
            return true;
        }

        /**
         * @static
         * @returns {boolean}
         */
        static get isEntityInstance() {
            return false;
        }

        /**
         * @static
         * @returns {boolean}
         */
        static get isEntityClass() {
            return true;
        }

        /**
         * Update relation on this class entity with provided data.
         *
         * Any relation, regardless of their type, are processed as removal
         * of provided value.
         *
         * Key should be named after relation names, and each values should be
         * either local id(s) or entity(ies) that respect the definition of
         * this relation. Special value `null` can be used to remove all
         * relations of provided relation name.
         *
         * @static
         * @param {Object|string} data
         */
        static unlink(data) {
            this.__unlink(this, data);
        }

        /**
         * Update this class entity with provided data.
         *
         * Provided data is used to update this class entity for the 1st time.
         * These data should be explicitly handled in `static _update()` method,
         * otherwise they are ignored.
         *
         * @static
         * @param {Object} data
         */
        static update(data) {
            this.__update(this, data);
        }

        /**
         * This method deletes this instance entity. After this operation, it's
         * as if this entity never existed. Note that relation are removed,
         * which may delete more relations if some of them are causal.
         */
        delete() {
            this.constructor.__delete(this);
        }

        /**
         * @returns {boolean}
         */
        get isEntity() {
            return true;
        }

        /**
         * @returns {boolean}
         */
        get isEntityClass() {
            return false;
        }

        /**
         * @returns {boolean}
         */
        get isEntityInstance() {
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
            this.constructor.__link(this, data);
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
            this.constructor.__unlink(this, data);
        }

        /**
         * Update this instance entity with provided data.
         *
         * Provided data is used to update this instance entity for the 1st time.
         * These data should be explicitly handled in `_update()` method,
         * otherwise they are ignored.
         *
         * @param {Object} data
         */
        update(data) {
            this.constructor.__update(this, data);
        }

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        /**
         * This method provide a list of all attributes of this class. This
         * method must be overriden by entity classes that make use of class
         * entities, and it should list all names of these attributes
         * (relations excluded).
         *
         * This is a technical necessity due to store state not observing
         * functions, which classes are. The workaround with class entities is
         * to put their state in another object (namely `this.observable`), but
         * in order to configure getter on class entities, all these attribute
         * names should be known at the moment of initializing this class entity.
         * If this method is not properly configured,
         * `<ClassEntity>.<attributeName>` does not redirect to
         * `<ClassEntity>.observable.<attributeName>`.
         *
         * @static
         * @private
         * @returns {string[]}
         */
        static _getListOfClassAttributeNames() {
            return [];
        }

        /**
         * This method is called when the class entity is initialized or
         * updated with provided data. This method should be overriden in order
         * to manage the data, otherwise they are ignored.
         *
         * @static
         * @private
         * @abstract
         * @param {Object} data
         */
        static _update(data) {}

        /**
         * Any assignment to class as attribute or stored relation should pass
         * through this function. This is useful in order to hide the technical
         * workaround to make class entities observable. Indeed, since classes
         * are not observed (due to being functions), they have to write state
         * somewhere else that is observed.
         *
         * @static
         * @private
         * @param {Object} data
         */
        static _write(data) {
            Object.assign(this.observable, data);
        }

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
            return _.uniqueId(`${this.constructor.localId}_`);
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

        /**
         * Any assignment to instance as attribute or stored relation should
         * pass through this function. This is useful in order to hide the
         * technical workaround to make class entities observable.
         *
         * @private
         * @param {Object} data
         */
        _write(data) {
            Object.assign(this, data);
        }

        //--------------------------------------------------------------------------
        // Internal
        //--------------------------------------------------------------------------

        /**
         * Technical management of deletion of provided entity. Should never
         * be called/overriden outside of this file.
         *
         * @static
         * @param {mail.messaging.entity.Entity} entity instance or class
         */
        static __delete(entity) {
            const { state } = this.env.store;
            if (!this.get(entity)) {
                // Entity has already been deleted.
                // (e.g. unlinking one of its reverse relation was causal)
                return;
            }
            const relations = entity.relations;
            const data = {};
            for (const relationName in relations) {
                const relation = relations[relationName];
                if (relation.isCausal) {
                    switch (relation.type) {
                        case 'one2one':
                        case 'many2one':
                            if (entity[relationName]) {
                                entity[relationName].delete();
                            }
                            break;
                        case 'one2many':
                        case 'many2many':
                            for (const relatedEntity of entity[relationName]) {
                                relatedEntity.delete();
                            }
                            break;
                    }
                }
                data[relationName] = null;
            }
            entity.unlink(data);
            delete state.entities[entity.localId];
            if (entity.isEntityClass) {
                delete state.__classEntityObservables[entity.localId];
            }
        }

        /**
         * Technical management of initialisation of provided entity. Should
         * never be called/overriden outside of this file.
         *
         * @static
         * @private
         * @param {mail.messaging.entity.Entity} entity instance or class
         */
        static __init(entity) {
            const relations = this.relations;
            for (const relationName in relations) {
                const relation = relations[relationName];
                if (['one2many', 'many2many'].includes(relation.type)) {
                    // Ensure X2many relations are arrays by defaults.
                    const storedRelationName = this.__getStoredRelationName(relationName);
                    entity._write({ [storedRelationName]: [] });
                }
                // compute getters
                Object.defineProperty(entity, relationName, {
                    get: () => {
                        const relation = relations[relationName];
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
         * Technical management of updating relations (link) of provided entity.
         * Should never be called/overriden outside of this file.
         *
         * @static
         * @private
         * @param {mail.messaging.entity.Entity} entity class or entity
         * @param {Object} data
         */
        static __link(entity, data) {
            const relations = this.relations;
            for (const [relationName, relationValue] of Object.entries(data)) {
                const relation = relations[relationName];
                switch (relation.type) {
                    case 'one2one':
                        this.__linkSingleOne2One(entity, {
                            relationName,
                            relationValue,
                        });
                        break;
                    case 'one2many':
                        this.__linkSingleOne2Many(entity, {
                            relationName,
                            relationValue,
                        });
                        break;
                    case 'many2one':
                        this.__linkSingleMany2One(entity, {
                            relationName,
                            relationValue,
                        });
                        break;
                    case 'many2many':
                        this.__linkSingleMany2Many(entity, {
                            relationName,
                            relationValue,
                        });
                        break;
                }
            }
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
            const relation = this.relations[relationName];
            const storedRelationName = this.__getStoredRelationName(relationName);
            const prevValue = entity[storedRelationName];
            const value = relationValue instanceof Array
                ? relationValue.map(e => e.isEntity ? e.localId: e)
                : [relationValue.isEntity ? relationValue.localId : relationValue];
            if (value.every(valueItem => prevValue.includes(valueItem))) {
                // Do not alter relations if unchanged.
                return;
            }
            entity._write({
                [storedRelationName]: [...new Set(entity[storedRelationName].concat(value))],
            });
            for (const valueItem of value) {
                if (prevValue.includes(valueItem)) {
                    continue;
                }
                const RelatedEntity = this.env.entities[relation.to];
                const related = RelatedEntity.get(valueItem);
                const storedRelatedRelationName =
                    RelatedEntity.__getStoredRelationName(relation.inverse);
                related._write({
                    [storedRelatedRelationName]: [
                        ...new Set(related[storedRelatedRelationName].concat([entity.localId]))
                    ],
                });
            }
        }

        /**
         * Technical management of updating a link operation of provided
         * relation of type many2one. Should never be called/overriden outside
         * of this file.
         *
         * @static
         * @private
         * @param {mail.messaging.entity.Entity} entity instance or class
         * @param {Object} param1
         * @param {string} param1.relationName
         * @param {string|mail.messaging.entity.Entity} param1.relationValue
         */
        static __linkSingleMany2One(entity, { relationName, relationValue }) {
            const relation = this.relations[relationName];
            const storedRelationName = this.__getStoredRelationName(relationName);
            const prevValue = entity[storedRelationName];
            const value = relationValue.isEntity ? relationValue.localId : relationValue;
            if (value === entity[storedRelationName]) {
                // Do not alter relations if unchanged.
                return;
            }
            entity._write({ [storedRelationName]: value });
            const RelatedEntity = this.env.entities[relation.to];
            if (prevValue) {
                const related = RelatedEntity.get(prevValue);
                if (!related) {
                    // prev Entity has already been deleted.
                    return;
                }
                const storedRelatedRelationName =
                    RelatedEntity.__getStoredRelationName(relation.inverse);
                related._write({
                    [storedRelatedRelationName]:
                        related[storedRelatedRelationName].filter(
                            valueItem => valueItem !== entity.localId
                        ),
                });
                if (relation.isCausal) {
                    related.delete();
                }
            }
            const related = RelatedEntity.get(value);
            const storedRelatedRelationName =
                RelatedEntity.__getStoredRelationName(relation.inverse);
            related._write({
                [storedRelatedRelationName]:
                    related[storedRelatedRelationName].concat([entity.localId]),
            });
        }

        /**
         * Technical management of updating a link operation of provided
         * relation of type one2many. Should never be called/overriden outside
         * of this file.
         *
         * @static
         * @private
         * @param {mail.messaging.entity.Entity} entity instance or class
         * @param {Object} param1
         * @param {string} param1.relationName
         * @param {string|mail.messaging.entity.Entity|<string|mail.messaging.entity.Entity>[]} param1.relationValue
         */
        static __linkSingleOne2Many(entity, { relationName, relationValue }) {
            const relation = this.relations[relationName];
            const storedRelationName = this.__getStoredRelationName(relationName);
            const prevValue = entity[storedRelationName];
            const value = relationValue instanceof Array
                ? relationValue.map(e => e.isEntity ? e.localId: e)
                : [relationValue.isEntity ? relationValue.localId : relationValue];
            if (value.every(valueItem => prevValue.includes(valueItem))) {
                // Do not alter relations if unchanged.
                return;
            }
            entity._write({
                [storedRelationName]: [...new Set(entity[storedRelationName].concat(value))],
            });
            for (const valueItem of value) {
                if (prevValue.includes(valueItem)) {
                    continue;
                }
                const RelatedEntity = this.env.entities[relation.to];
                const related = RelatedEntity.get(valueItem);
                const storedRelatedRelationName =
                    RelatedEntity.__getStoredRelationName(relation.inverse);
                related._write({ [storedRelatedRelationName]: entity.localId });
            }
        }

        /**
         * Technical management of updating a link operation of provided
         * relation of type one2one. Should never be called/overriden outside
         * of this file.
         *
         * @static
         * @private
         * @param {mail.messaging.entity.Entity} entity instance or class
         * @param {Object} param1
         * @param {string} param1.relationName
         * @param {string|mail.messaging.entity.Entity} param1.relationValue
         */
        static __linkSingleOne2One(entity, { relationName, relationValue }) {
            const relation = this.relations[relationName];
            const storedRelationName = this.__getStoredRelationName(relationName);
            const prevValue = entity[storedRelationName];
            const value = relationValue.isEntity ? relationValue.localId : relationValue;
            entity._write({ [storedRelationName]: value });
            const RelatedEntity = this.env.entities[relation.to];
            if (prevValue) {
                const related = RelatedEntity.get(prevValue);
                const storedRelatedRelationName =
                    RelatedEntity.__getStoredRelationName(relation.inverse);
                related._write({ [storedRelatedRelationName]: undefined });
                if (relation.isCausal) {
                    related.delete();
                }
            }
            const related = RelatedEntity.get(value);
            const storedRelatedRelationName = RelatedEntity.__getStoredRelationName(relation.inverse);
            related._write({ [storedRelatedRelationName]: entity.localId });
        }

        /**
         * Technical management of updating relations (unlink) of provided entity.
         * Should never be called/overriden outside of this file.
         *
         * @static
         * @param {mail.messaging.entity.Entity} entity
         * @param {Object|string} data
         */
        static __unlink(entity, data) {
            if (!this.get(entity)) {
                // Entity has already been deleted.
                // (e.g. unlinking one of its reverse relation was causal)
                return;
            }
            const relations = this.relations;
            for (const [relationName, relationValue] of Object.entries(data)) {
                const relation = relations[relationName];
                switch (relation.type) {
                    case 'one2one':
                        this.__unlinkSingleOne2One(entity, { relationName });
                        break;
                    case 'one2many':
                        this.__unlinkSingleOne2Many(entity, { relationName, relationValue });
                        break;
                    case 'many2one':
                        this.__unlinkSingleMany2One(entity, { relationName });
                        break;
                    case 'many2many':
                        this.__unlinkSingleMany2Many(entity, { relationName, relationValue });
                        break;
                }
            }
        }

        /**
         * Technical management of unlink operation of provided relation of
         * type many2many. Should never be called/overriden outside of this file.
         *
         * @static
         * @private
         * @param {mail.messaging.entity.Entity} entity instance or class
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
            const relation = this.relations[relationName];
            const storedRelationName = this.__getStoredRelationName(relationName);
            const value = relationValue === null
                ? [...entity[storedRelationName]]
                : relationValue instanceof Array
                ? relationValue.map(e => e.isEntity ? e.localId: e)
                : [relationValue.isEntity ? relationValue.localId : relationValue];
            entity._write({
                [storedRelationName]: entity[storedRelationName].filter(
                    valueItem => !value.includes(valueItem)
                ),
            });
            const RelatedEntity = this.env.entities[relation.to];
            for (const valueItem of value) {
                const related = RelatedEntity.get(valueItem);
                const storedRelatedRelationName =
                    RelatedEntity.__getStoredRelationName(relation.inverse);
                related._write({
                    [storedRelatedRelationName]:
                        related[storedRelatedRelationName].filter(
                            valueItem => valueItem !== entity.localId
                        ),
                });
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
            const relation = this.relations[relationName];
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
            const relation = this.relations[relationName];
            const storedRelationName = this.__getStoredRelationName(relationName);
            const prevValue = entity[storedRelationName];
            const value = relationValue === null
                ? [...entity[storedRelationName]]
                : relationValue instanceof Array
                ? relationValue.map(e => e.isEntity ? e.localId: e)
                : [relationValue.isEntity ? relationValue.localId : relationValue];
            entity._write({
                [storedRelationName]: entity[storedRelationName].filter(
                    valueItem => !value.includes(valueItem)
                ),
            });
            if (prevValue) {
                const RelatedEntity = this.env.entities[relation.to];
                for (const valueItem of value) {
                    const related = RelatedEntity.get(valueItem);
                    const storedRelatedRelationName =
                        RelatedEntity.__getStoredRelationName(relation.inverse);
                    related._write({
                        [storedRelatedRelationName]: undefined,
                    });
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
         * @param {mail.messaging.entity.Entity} entity instance or class
         * @param {Object} param1
         * @param {string} param1.relationName
         */
        static __unlinkSingleOne2One(entity, { relationName }) {
            if (!this.get(entity)) {
                // Entity has already been deleted.
                // (e.g. unlinking one of its reverse relation was causal)
                return;
            }
            const relation = this.relations[relationName];
            const storedRelationName = this.__getStoredRelationName(relationName);
            const prevValue = entity[storedRelationName];
            entity._write({ [storedRelationName]: undefined });
            const RelatedEntity = this.env.entities[relation.to];
            if (prevValue) {
                const related = RelatedEntity.get(prevValue);
                const storedRelatedRelationName =
                    RelatedEntity.__getStoredRelationName(relation.inverse);
                related._write({ [storedRelatedRelationName]: undefined });
            }
        }

        /**
         * Technical management of update of provided entity. Should never
         * be called/overriden outside of this file.
         *
         * @static
         * @private
         * @param {mail.messaging.entity.Entity} entity
         * @param {Object} [data={}]
         */
        static __update(entity, data = {}) {
            entity._update(data);
        }

    }

    Object.assign(Entity, {
        /**
         * Registry containing data to make Entity classes. Entity classes should
         * register themselves through static method `Entity.registerNewEntity()`.
         *
         * Format:
         *
         *   <relation-name>:
         *      {
         *         Factory: function that produce Entity class.
         *         plugins: list of extensions to apply on the Entity class.
         *                  Each entity classes should itself be designed to process
         *                  these plugins.
         *      }
         */
        registry: {},
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
        relations: {
            /**
             * Related dialog of entity when dialog content is directly linked to
             * an entity that models a UI component, such as AttachmentViewer. Such
             * entities must be created from @see `Dialog.open()` and cannot be
             * singleton entities.
             */
            dialog: {
                inverse: 'entity',
                isCausal: true,
                to: 'Dialog',
                type: 'one2one',
            },
        },
    });

    return Entity;
}

registerNewEntity('Entity', EntityFactory);

});
