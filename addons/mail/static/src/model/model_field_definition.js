odoo.define('mail/static/src/model/model_field_definition.js', function (require) {
'use strict';

/**
 * Class whose instances represent field on a model.
 * These field definitions are generated from declared fields in static prop
 * `fields` on the model.
 */
class ModelFieldDefinition {

    constructor({
        compute,
        default: def,
        dependencies = [],
        dependents = [],
        env,
        fieldName,
        fieldType,
        hashes: extraHashes = [],
        inverse,
        isCausal = false,
        related,
        relationType,
        to,
    } = {}) {
        const id = _.uniqueId('FieldDefinition_');
        /**
         * If set, this field acts as a computed field, and this prop
         * contains the name of the instance method that computes the value
         * for this field. This compute method is called on creation of record
         * and whenever some of its dependencies change. @see dependencies
         */
        this.compute = compute;
        /**
         * Default value for this field. Used on creation of this field, to
         * set a value by default. Could also be a function with no params
         * which, on call, returns the default value for this field.
         */
        this.default = def;
        /**
         * List of field on current record that this field depends on for its
         * `compute` method. Useful to determine whether this field should be
         * registered for recomputation when some record fields have changed.
         * This list must be declared in model definition, or compute method
         * is only computed once.
         */
        this.dependencies = dependencies;
        /**
         * List of fields that are dependent of this field. They should never
         * be declared, and are automatically generated while processing
         * declared fields. This is populated by compute `dependencies` and
         * `related`.
         */
        this.dependents = dependents;
        /**
         * The messaging env.
         */
        this.env = env;
        /**
         * Name of the field in the definition of fields on model.
         */
        this.fieldName = fieldName;
        /**
         * Type of this field. 2 types of fields are currently supported:
         *
         *   1. 'attribute': fields that store primitive values like integers,
         *                   booleans, strings, objects, array, etc.
         *
         *   2. 'relation': fields that relate to some other records.
         */
        this.fieldType = fieldType;
        /**
         * List of hashes registered on this field definition. Technical
         * prop that is specifically used in processing of dependent
         * fields, useful to clearly identify which fields of a relation are
         * dependents and must be registered for computed. Indeed, not all
         * related records may have a field that depends on changed field,
         * especially when dependency is defined on sub-model on a relation in
         * a super-model.
         *
         * To illustrate the purpose of this hash, suppose following definition
         * of models and fields:
         *
         * - 3 models (A, B, C) and 3 fields (x, y, z)
         * - A.fields: { x: one2one(C, inverse: x') }
         * - B extends A
         * - B.fields: { z: related(x.y) }
         * - C.fields: { y: attribute }
         *
         * Visually:
         *               x'
         *          <-----------
         *        A -----------> C { y }
         *        ^      x
         *        |
         *        | (extends)
         *        |
         *        B { z = x.y }
         *
         * If z has a dependency on x.y, it means y has a dependent on x'.z.
         * Note that field z exists on B but not on all A. To determine which
         * kinds of records in relation x' are dependent on y, y is aware of an
         * hash on this dependent, and any dependents who has this hash in list
         * of hashes are actual dependents.
         */
        this.hashes = extraHashes.concat([id]);
        /**
         * Identification for this field definition. Useful to map a dependent
         * from a dependency. Indeed, declared field definitions use
         * 'dependencies' but technical process need inverse as 'dependents'.
         * Dependencies just need name of fields, but dependents cannot just
         * rely on inverse field names because these dependents are a subset.
         */
        this.id = id;
        /**
         * This prop only makes sense in a relational field. This contains
         * the name of the field name in the inverse relation. This may not
         * be defined in declared field definitions, but processed relational
         * field definitions always have inverses.
         */
        this.inverse = inverse;
        /**
         * This prop only makes sense in a relational field. If set, when this
         * relation is removed, the related record is automatically deleted.
         */
        this.isCausal = isCausal;
        /**
         * If set, this field acts as a related field, and this prop contains
         * a string that references the related field. It should have the
         * following format: '<relationName>.<relatedFieldName>', where
         * <relationName> is a relational field name on this model or a parent
         * model (note: could itself be computed or related), and
         * <relatedFieldName> is the name of field on the records that are
         * related to current record from this relation. When there are more
         * than one record in the relation, it maps all related fields per
         * record in relation.
         *
         * FIXME: currently flatten map due to bug, improvement is planned
         * see Task-id 2261221
         */
        this.related = related;
        /**
         * This prop only makes sense in a relational field. Determine which
         * type of relation there is between current record and other records.
         * 4 types of relation are supported: 'one2one', 'one2many', 'many2one'
         * and 'many2many'.
         */
        this.relationType = relationType;
        /**
         * This prop only makes sense in a relational field. Determine which
         * model name this relation refers to.
         */
        this.to = to;

        if (!this.default && this.fieldType === 'relation') {
            // default value for relational fields is the empty command
            this.default = [];
        }
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Combine current field definition with provided field definition and
     * return the combined field definition. Useful to track list of hashes of
     * a given field, which is necessary for the working of dependent fields
     * (computed and related fields).
     *
     * @param {ModelFieldDefinition} field
     * @returns {ModelFieldDefinition}
     */
    combine(field) {
        return new ModelFieldDefinition(Object.assign({}, this, {
            dependencies: this.dependencies.concat(field.dependencies),
            hashes: this.hashes.concat(field.hashes),
        }));
    }

    /**
     * Compute method when this field is related.
     *
     * @private
     * @param {mail.model} record
     */
    computeRelated(record) {
        const [relationName, relatedFieldName] = this.related.split('.');
        const Model = record.constructor;
        const relationField = Model.__fieldMap[relationName];
        if (['one2many', 'many2many'].includes(relationField.relationType)) {
            const newVal = [];
            for (const otherRecord of record[relationName]()) {
                const OtherModel = otherRecord.constructor;
                const otherField = OtherModel.__fieldMap[relatedFieldName];
                const otherValue = otherField.get(otherRecord);
                if (otherValue) {
                    if (otherValue instanceof Array) {
                        // avoid nested array if otherField is x2many too
                        // TODO IMP task-2261221
                        for (const v of otherValue) {
                            newVal.push(v);
                        }
                    } else {
                        newVal.push(otherValue);
                    }
                }
            }
            if (this.fieldType === 'relation') {
                return [['replace', newVal]];
            }
            return newVal;
        }
        const otherRecord = record[relationName]();
        if (otherRecord) {
            const OtherModel = otherRecord.constructor;
            const otherField = OtherModel.__fieldMap[relatedFieldName];
            const newVal = otherField.get(otherRecord);
            if (this.fieldType === 'relation') {
                if (newVal) {
                    return [['replace', newVal]];
                } else {
                    return [['unlink-all']];
                }
            }
            return newVal;
        }
        if (this.fieldType === 'relation') {
            return [];
        }
    }

    /**
     * Get the value associated to this field. Relations must convert record
     * local ids to records.
     *
     * @param {mail.model} record
     * @returns {any}
     */
    get(record) {
        if (this.fieldType === 'attribute') {
            return this.read(record);
        }
        if (this.fieldType === 'relation') {
            if (['one2one', 'many2one'].includes(this.relationType)) {
                return this.read(record);
            }
            return [...this.read(record)];
        }
        throw new Error(`cannot get field with unsupported type ${this.fieldType}.`);
    }

}

return ModelFieldDefinition;

});
