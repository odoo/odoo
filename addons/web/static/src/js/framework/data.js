odoo.define('web.data', function (require) {
"use strict";

var core = require('web.core');
var Model = require('web.Model');
var session = require('web.session');
var pyeval = require('web.pyeval');
var utils = require('web.utils');

var Class = core.Class;
var mixins = core.mixins;
var _t = core._t;

/**
 * Serializes the sort criterion array of a dataset into a form which can be
 * consumed by OpenERP's RPC APIs.
 *
 * @param {Array} criterion array of fields, from first to last criteria, prefixed with '-' for reverse sorting
 * @returns {String} SQL-like sorting string (``ORDER BY``) clause
 */
function serialize_sort(criterion) {
    return _.map(criterion,
        function (criteria) {
            if (criteria[0] === '-') {
                return criteria.slice(1) + ' DESC';
            }
            return criteria + ' ASC';
        }).join(', ');
}

/**
 * Reverse of the serialize_sort function: convert an array of SQL-like sort 
 * descriptors into a list of fields prefixed with '-' if necessary.
 */
function deserialize_sort(criterion) {
    return _.map(criterion, function (criteria) {
        var split = _.without(criteria.split(' '), '');
        return (split[1] && split[1].toLowerCase() === 'desc' ? '-' : '') + split[0];
    });
}

var Query = Class.extend({
    init: function (model, fields) {
        this._model = model;
        this._fields = fields;
        this._filter = [];
        this._context = {};
        this._lazy = true;
        this._limit = false;
        this._offset = 0;
        this._order_by = [];
    },
    clone: function (to_set) {
        to_set = to_set || {};
        var q = new Query(this._model, this._fields);
        q._context = this._context;
        q._filter = this._filter;
        q._lazy = this._lazy;
        q._limit = this._limit;
        q._offset = this._offset;
        q._order_by = this._order_by;

        for(var key in to_set) {
            if (!to_set.hasOwnProperty(key)) { continue; }
            switch(key) {
            case 'filter':
                q._filter = new CompoundDomain(
                        q._filter, to_set.filter);
                break;
            case 'context':
                q._context = new CompoundContext(
                        q._context, to_set.context);
                break;
            case 'lazy':
            case 'limit':
            case 'offset':
            case 'order_by':
                q['_' + key] = to_set[key];
            }
        }
        return q;
    },
    _execute: function (options) {
        var self = this;
        options = options || {};
        return session.rpc('/web/dataset/search_read', {
            model: this._model.name,
            fields: this._fields || false,
            domain: pyeval.eval('domains',
                    [this._model.domain(this._filter)]),
            context: pyeval.eval('contexts',
                    [this._model.context(this._context)]),
            offset: this._offset,
            limit: this._limit,
            sort: serialize_sort(this._order_by)
        }, options).then(function (results) {
            self._count = results.length;
            return results.records;
        }, null);
    },
    /**
     * Fetches the first record matching the query, or null
     *
     * @param {Object} [options] additional options for the rpc() method
     * @returns {jQuery.Deferred<Object|null>}
     */
    first: function (options) {
        var self = this;
        return this.clone({limit: 1})._execute(options).then(function (records) {
            delete self._count;
            if (records.length) { return records[0]; }
            return null;
        });
    },
    /**
     * Fetches all records matching the query
     *
     * @param {Object} [options] additional options for the rpc() method
     * @returns {jQuery.Deferred<Array<>>}
     */
    all: function (options) {
        return this._execute(options);
    },
    /**
     * Fetches the number of records matching the query in the database
     *
     * @returns {jQuery.Deferred<Number>}
     */
    count: function () {
        if (this._count !== undefined) { return $.when(this._count); }
        return this._model.call(
            'search_count', [this._filter], {
                context: this._model.context(this._context)});
    },
    /**
     * Performs a groups read according to the provided grouping criterion
     *
     * @param {String|Array<String>} grouping
     * @returns {jQuery.Deferred<Array<openerp.web.QueryGroup>> | null}
     */
    group_by: function (grouping) {
        var ctx = pyeval.eval(
            'context', this._model.context(this._context));

        // undefined passed in explicitly (!)
        if (_.isUndefined(grouping)) {
            grouping = [];
        }

        if (!(grouping instanceof Array)) {
            grouping = _.toArray(arguments);
        }
        if (_.isEmpty(grouping) && !ctx.group_by_no_leaf) {
            return null;
        }
        var raw_fields = _.map(grouping.concat(this._fields || []), function (field) {
            return field.split(':')[0];
        });

        var self = this;
        return this._model.call('read_group', {
            groupby: grouping,
            fields: _.uniq(raw_fields),
            domain: this._model.domain(this._filter),
            context: ctx,
            offset: this._offset,
            lazy: this._lazy,
            limit: this._limit,
            orderby: serialize_sort(this._order_by) || false
        }).then(function (results) {
            return _(results).map(function (result) {
                // FIX: querygroup initialization
                result.__context = result.__context || {};
                result.__context.group_by = result.__context.group_by || [];
                _.defaults(result.__context, ctx);
                var grouping_fields = self._lazy ? [grouping[0]] : grouping;
                return new QueryGroup(
                    self._model.name, grouping_fields, result);
            });
        });
    },
    /**
     * Creates a new query with the union of the current query's context and
     * the new context.
     *
     * @param context context data to add to the query
     * @returns {openerp.web.Query}
     */
    context: function (context) {
        if (!context) { return this; }
        return this.clone({context: context});
    },
    /**
     * Creates a new query with the union of the current query's filter and
     * the new domain.
     *
     * @param domain domain data to AND with the current query filter
     * @returns {openerp.web.Query}
     */
    filter: function (domain) {
        if (!domain) { return this; }
        return this.clone({filter: domain});
    },
    /**
     * Creates a new query with the provided parameter lazy replacing the current
     * query's own.
     *
     * @param {Boolean} lazy indicates if the read_group should return only the 
     * first level of groupby records, or should return the records grouped by
     * all levels at once (so, it makes only 1 db request).
     * @returns {openerp.web.Query}
     */
    lazy: function (lazy) {
        return this.clone({lazy: lazy});
    },
    /**
     * Creates a new query with the provided limit replacing the current
     * query's own limit
     *
     * @param {Number} limit maximum number of records the query should retrieve
     * @returns {openerp.web.Query}
     */
    limit: function (limit) {
        return this.clone({limit: limit});
    },
    /**
     * Creates a new query with the provided offset replacing the current
     * query's own offset
     *
     * @param {Number} offset number of records the query should skip before starting its retrieval
     * @returns {openerp.web.Query}
     */
    offset: function (offset) {
        return this.clone({offset: offset});
    },
    /**
     * Creates a new query with the provided ordering parameters replacing
     * those of the current query
     *
     * @param {String...} fields ordering clauses
     * @returns {openerp.web.Query}
     */
    order_by: function (fields) {
        if (fields === undefined) { return this; }
        if (!(fields instanceof Array)) {
            fields = _.toArray(arguments);
        }
        if (_.isEmpty(fields)) { return this; }
        return this.clone({order_by: fields});
    }
});

var QueryGroup = Class.extend({
    init: function (model, grouping_fields, read_group_group) {
        // In cases where group_by_no_leaf and no group_by, the result of
        // read_group has aggregate fields but no __context or __domain.
        // Create default (empty) values for those so that things don't break
        var fixed_group = _.extend(
            {__context: {group_by: []}, __domain: []},
            read_group_group);

        var count_key = (grouping_fields[0] && grouping_fields[0].split(':')[0]) + '_count';
        var aggregates = {};
        _(fixed_group).each(function (value, key) {
            if (key.indexOf('__') === 0
                    || _.contains(grouping_fields, key)
                    || (key === count_key)) {
                return;
            }
            aggregates[key] = value || 0;
        });

        this.model = new Model(
            model, fixed_group.__context, fixed_group.__domain);

        var group_size = fixed_group[count_key] || fixed_group.__count || 0;
        var leaf_group = fixed_group.__context.group_by.length === 0;

        var value = (grouping_fields.length === 1) 
                ? fixed_group[grouping_fields[0]]
                : _.map(grouping_fields, function (field) { return fixed_group[field]; });
        var grouped_on = (grouping_fields.length === 1) 
                ? grouping_fields[0] 
                : grouping_fields;
        this.attributes = {
            folded: !!(fixed_group.__fold),
            grouped_on: grouped_on,
            // if terminal group (or no group) and group_by_no_leaf => use group.__count
            length: group_size,
            value: value,
            // A group is open-able if it's not a leaf in group_by_no_leaf mode
            has_children: !(leaf_group && fixed_group.__context.group_by_no_leaf),

            aggregates: aggregates
        };
    },
    get: function (key) {
        return this.attributes[key];
    },
    subgroups: function () {
        return this.model.query().group_by(this.model.context().group_by);
    },
    query: function () {
        return this.model.query.apply(this.model, arguments);
    }
});

var DataSet =  Class.extend(mixins.PropertiesMixin, {
    /**
     * Collection of OpenERP records, used to share records and the current selection between views.
     *
     * @constructs instance.web.DataSet
     *
     * @param {String} model the OpenERP model this dataset will manage
     */
    init: function(parent, model, context) {
        mixins.PropertiesMixin.init.call(this);
        this.model = model;
        this.context = context || {};
        this.index = null;
        this._sort = [];
        this._model = new Model(model, context);
        this.orderer = new utils.DropMisordered();
    },
    previous: function () {
        this.index -= 1;
        if (!this.ids.length) {
            this.index = null;
        } else if (this.index < 0) {
            this.index = this.ids.length - 1;
        }
        return this;
    },
    next: function () {
        this.index += 1;
        if (!this.ids.length) {
            this.index = null;
        } else if (this.index >= this.ids.length) {
            this.index = 0;
        }
        return this;
    },
    select_id: function(id) {
        var idx = this.get_id_index(id);
        if (idx === null) {
            return false;
        } else {
            this.index = idx;
            return true;
        }
    },
    get_id_index: function(id) {
        for (var i=0, ii=this.ids.length; i<ii; i++) {
            // Here we use type coercion because of the mess potentially caused by
            // OpenERP ids fetched from the DOM as string. (eg: dhtmlxcalendar)
            // OpenERP ids can be non-numeric too ! (eg: recursive events in calendar)
            if (id == this.ids[i]) {
                return i;
            }
        }
        return null;
    },
    /**
     * Read records.
     *
     * @param {Array} ids identifiers of the records to read
     * @param {Array} [fields] fields to read and return, by default all fields are returned
     * @param {Object} [options]
     * @returns {$.Deferred}
     */
    read_ids: function (ids, fields, options) {
        if (_.isEmpty(ids))
            return $.Deferred().resolve([]);
            
        options = options || {};
        var method = 'read';
        var ids_arg = ids;
        var context = this.get_context(options.context);
        if (options.check_access_rule === true){
            method = 'search_read';
            ids_arg = [['id', 'in', ids]];
            context = new CompoundContext(context, {active_test: false});
        }
        return this._model.call(method,
                [ids_arg, fields || false],
                {context: context})
            .then(function (records) {
                if (records.length <= 1) { return records; }
                var indexes = {};
                for (var i = 0; i < ids.length; i++) {
                    indexes[ids[i]] = i;
                }
                records.sort(function (a, b) {
                    return indexes[a.id] - indexes[b.id];
                });
                return records;
        });
    },
    /**
     * Read a slice of the records represented by this DataSet, based on its
     * domain and context.
     *
     * @param {Array} [fields] fields to read and return, by default all fields are returned
     * @params {Object} [options]
     * @param {Number} [options.offset=0] The index from which selected records should be returned
     * @param {Number} [options.limit=null] The maximum number of records to return
     * @returns {$.Deferred}
     */
    read_slice: function (fields, options) {
        var self = this;
        options = options || {};
        var query = this._model.query(fields)
                .limit(options.limit || false)
                .offset(options.offset || 0)
                .all();
        return this.orderer.add(query).done(function (records) {
            self.ids = _(records).pluck('id');
        });
    },
    /**
     * Reads the current dataset record (from its index)
     *
     * @params {Array} [fields] fields to read and return, by default all fields are returned
     * @param {Object} [options.context] context data to add to the request payload, on top of the DataSet's own context
     * @returns {$.Deferred}
     */
    read_index: function (fields, options) {
        options = options || {};
        return this.read_ids([this.ids[this.index]], fields, options).then(function (records) {
            if (_.isEmpty(records)) { return $.Deferred().reject().promise(); }
            return records[0];
        });
    },
    /**
     * Reads default values for the current model
     *
     * @param {Array} [fields] fields to get default values for, by default all defaults are read
     * @param {Object} [options.context] context data to add to the request payload, on top of the DataSet's own context
     * @returns {$.Deferred}
     */
    default_get: function(fields, options) {
        options = options || {};
        return this._model.call('default_get',
            [fields], {context: this.get_context(options.context)});
    },
    /**
     * Creates a new record in db
     *
     * @param {Object} data field values to set on the new record
     * @param {Object} options Dictionary that can contain the following keys:
     *   - readonly_fields: Values from readonly fields that were updated by
     *     on_changes. Only used by the BufferedDataSet to make the o2m work correctly.
     * @returns {$.Deferred}
     */
    create: function(data, options) {
        var self = this;
        return this._model.call('create', [data], {
            context: this.get_context()
        }).done(function () {
            self.trigger('dataset_changed', data, options);
        });
    },
    /**
     * Saves the provided data in an existing db record
     *
     * @param {Number|String} id identifier for the record to alter
     * @param {Object} data field values to write into the record
     * @param {Object} options Dictionary that can contain the following keys:
     *   - context: The context to use in the server-side call.
     *   - readonly_fields: Values from readonly fields that were updated by
     *     on_changes. Only used by the BufferedDataSet to make the o2m work correctly.
     * @returns {$.Deferred}
     */
    write: function (id, data, options) {
        options = options || {};
        var self = this;
        return this._model.call('write', [[id], data], {
            context: this.get_context(options.context)
        }).done(function () {
            self.trigger('dataset_changed', id, data, options);
        });
    },
    /**
     * Deletes an existing record from the database
     *
     * @param {Number|String} ids identifier of the record to delete
     */
    unlink: function(ids) {
        var self = this;
        return this._model.call('unlink', [ids], {
            context: this.get_context()
        }).done(function () {
            self.trigger('dataset_changed', ids);
        });
    },
    /**
     * Calls an arbitrary RPC method
     *
     * @param {String} method name of the method (on the current model) to call
     * @param {Array} [args] arguments to pass to the method
     * @param {Function} callback
     * @param {Function} error_callback
     * @returns {$.Deferred}
     */
    call: function (method, args) {
        return this._model.call(method, args);
    },
    /**
     * Calls a button method, usually returning some sort of action
     *
     * @param {String} method
     * @param {Array} [args]
     * @returns {$.Deferred}
     */
    call_button: function (method, args) {
        return this._model.call_button(method, args);
    },
    /**
     * Fetches the "readable name" for records, based on intrinsic rules
     *
     * @param {Array} ids
     * @returns {$.Deferred}
     */
    name_get: function(ids) {
        return this._model.call('name_get', [ids], {context: this.get_context()});
    },
    /**
     * 
     * @param {String} name name to perform a search for/on
     * @param {Array} [domain=[]] filters for the objects returned, OpenERP domain
     * @param {String} [operator='ilike'] matching operator to use with the provided name value
     * @param {Number} [limit=0] maximum number of matches to return
     * @param {Function} callback function to call with name_search result
     * @returns {$.Deferred}
     */
    name_search: function (name, domain, operator, limit) {
        return this._model.call('name_search', {
            name: name || '',
            args: domain || false,
            operator: operator || 'ilike',
            context: this._model.context(),
            limit: limit || 0
        });
    },
    /**
     * @param name
     */
    name_create: function(name, context) {
        return this._model.call('name_create', [name], {context: this.get_context(context)});
    },
    exec_workflow: function (id, signal) {
        return this._model.exec_workflow(id, signal);
    },
    get_context: function(request_context) {
        return this._model.context(request_context);
    },
    /**
     * Reads or changes sort criteria on the dataset.
     *
     * If not provided with any argument, serializes the sort criteria to
     * an SQL-like form usable by OpenERP's ORM.
     *
     * If given a field, will set that field as first sorting criteria or,
     * if the field is already the first sorting criteria, will reverse it.
     *
     * @param {String} [field] field to sort on, reverses it (toggle from ASC to DESC) if already the main sort criteria
     * @param {Boolean} [force_reverse=false] forces inserting the field as DESC
     * @returns {String|undefined}
     */
    sort: function (field, force_reverse) {
        if (!field) {
            return serialize_sort(this._sort);
        }
        var reverse = force_reverse || (this._sort[0] === field);
        this._sort.splice.apply(
            this._sort, [0, this._sort.length].concat(
                _.without(this._sort, field, '-' + field)));

        this._sort.unshift((reverse ? '-' : '') + field);
        return undefined;
    },
    /**
     * Set the sort criteria on the dataset.  
     *
     * @param {Array} fields_list: list of fields order descriptors, as used by
     * Odoo's ORM (such as 'name desc', 'product_id', 'order_date asc')
     */
    set_sort: function (fields_list) {
        this._sort = deserialize_sort(fields_list);
    },
    size: function () {
        return this.ids.length;
    },
    alter_ids: function(n_ids) {
        this.ids = n_ids;
    },
    remove_ids: function (ids) {
        this.alter_ids(_(this.ids).difference(ids));
    },
    add_ids: function(ids, at) {
        var args = [at, 0].concat(_.difference(ids, this.ids));
        this.ids.splice.apply(this.ids, args);
    },
    /**
     * Resequence records.
     *
     * @param {Array} ids identifiers of the records to resequence
     * @returns {$.Deferred}
     */
    resequence: function (ids, options) {
        options = options || {};
        return session.rpc('/web/dataset/resequence', {
            model: this.model,
            ids: ids,
            context: pyeval.eval(
                'context', this.get_context(options.context)),
        }).then(function (results) {
            return results;
        });
    },
});

var DataSetStatic =  DataSet.extend({
    init: function(parent, model, context, ids) {
        this._super(parent, model, context);
        // all local records
        this.ids = ids || [];
    },
    read_slice: function (fields, options) {
        options = options || {};
        fields = fields || {};
        var offset = options.offset || 0,
            limit = options.limit || false;
        var end_pos = limit && limit !== -1 ? offset + limit : this.ids.length;
        return this.read_ids(this.ids.slice(offset, end_pos), fields, options);
    },
    set_ids: function (ids) {
        this.ids = ids;
        if (ids.length === 0) {
            this.index = null;
        } else if (this.index >= ids.length - 1) {
            this.index = ids.length - 1;
        }
    },
    unlink: function(ids) {
        this.set_ids(_.without.apply(null, [this.ids].concat(ids)));
        this.trigger('unlink', ids);
        return $.Deferred().resolve({result: true});
    },
});

var DataSetSearch = DataSet.extend({
    /**
     * @constructs instance.web.DataSetSearch
     * @extends instance.web.DataSet
     *
     * @param {Object} parent
     * @param {String} model
     * @param {Object} context
     * @param {Array} domain
     */
    init: function(parent, model, context, domain) {
        this._super(parent, model, context);
        this.domain = domain || [];
        this._length = null;
        this.ids = [];
        this._model = new Model(model, context, domain);
    },
    /**
     * Read a slice of the records represented by this DataSet, based on its
     * domain and context.
     *
     * @params {Object} options
     * @param {Array} [options.fields] fields to read and return, by default all fields are returned
     * @param {Object} [options.context] context data to add to the request payload, on top of the DataSet's own context
     * @param {Array} [options.domain] domain data to add to the request payload, ANDed with the dataset's domain
     * @param {Number} [options.offset=0] The index from which selected records should be returned
     * @param {Number} [options.limit=null] The maximum number of records to return
     * @returns {$.Deferred}
     */
    read_slice: function (fields, options) {
        options = options || {};
        var self = this;
        var q = this._model.query(fields || false)
            .filter(options.domain)
            .context(options.context)
            .offset(options.offset || 0)
            .limit(options.limit || false);
        q = q.order_by.apply(q, this._sort);

        return q.all().done(function (records) {
            // FIXME: not sure about that one, *could* have discarded count
            q.count().done(function (count) { self._length = count; });
            self.ids = _(records).pluck('id');
        });
    },
    get_domain: function (other_domain) {
        return this._model.domain(other_domain);
    },
    alter_ids: function (ids) {
        this._super(ids);
        if (this.index !== null && this.index >= this.ids.length) {
            this.index = this.ids.length > 0 ? this.ids.length - 1 : 0;
        }
    },
    remove_ids: function (ids) {
        var before = this.ids.length;
        this._super(ids);
        if (this._length) {
            this._length -= (before - this.ids.length);
        }
    },
    unlink: function(ids, callback, error_callback) {
        var self = this;
        return this._super(ids).done(function() {
            self.remove_ids( ids);
            self.trigger("dataset_changed", ids, callback, error_callback);
        });
    },
    size: function () {
        if (this._length !== null) {
            return this._length;
        }
        return this._super();
    }
});

var BufferedDataSet = DataSetStatic.extend({
    virtual_id_prefix: "one2many_v_id_",
    debug_mode: true,
    init: function() {
        this._super.apply(this, arguments);
        this.reset_ids([]);
        this.last_default_get = {};
        this.running_reads = [];
        this.mutex = new utils.Mutex();
    },
    default_get: function(fields, options) {
        var self = this;
        return this._super(fields, options).done(function(res) {
            self.last_default_get = _.clone(res);
        });
    },
    get_cache: function (id) {
        if (!this.cache[id]) {
            this.cache[id] = {
                'id': id,
                'values': {},
                'from_read': {},
                'changes': {},
                'readonly_fields': {},
                'to_create': false,
                'to_delete': false};
        }
        return this.cache[id];
    },
    _update_cache: function (id, options) {
        // One should call this method after modifying this.from_read,
        // this.to_create or this.change. It updates this.cache and
        // this.readonly_fields.
        var cached = this.get_cache(id);
        if (options) {
            _.extend(cached.from_read, options.from_read);
            _.extend(cached.changes, options.changes);
            _.extend(cached.readonly_fields, options.readonly_fields);
            // discard values from cached.changes that are in cached.from_read
            _.each(cached.changes, function (v, k) {
                if (cached.from_read[k] === v) {
                    delete cached.changes[k];
                }
            });
            if (options.to_create !== undefined) cached.to_create = options.to_create;
            if (options.to_delete !== undefined) cached.to_delete = options.to_delete;
        }
        cached.values = _.extend({'id': id}, cached.from_read, cached.changes, cached.readonly_fields);
        return cached;
    },
    create: function(data, options) {        
        var changes = _.extend({}, this.last_default_get, data);
        var cached = this._update_cache(_.uniqueId(this.virtual_id_prefix), _.extend({'changes': changes, 'to_create': true}, options));
        this.trigger("dataset_changed", data, options);
        return $.Deferred().resolve(cached.id);
    },
    write: function (id, data, options) {
        var self = this;
        var cached = this.get_cache(id);

        // if update after a remove, it's like an add before updating
        cached.to_delete = false;

        // apply change
        var def = $.Deferred();
        this.mutex.exec(function () {
            var dirty = false;
            _.each(data, function (v, k) {
                if (!_.isEqual(v, cached.values[k])) {
                    dirty = true;
                    if (_.isEqual(v, cached.from_read[k])) { // clean changes
                        delete cached.changes[k];
                    } else {
                        cached.changes[k] = v;
                    }
                } else {
                    delete data[k];
                }
            });
            self._update_cache(id, options);

            if (dirty) {
                self.trigger("dataset_changed", id, data, options);
            }

            return def.resolve(data).promise();
        });

        return def;
    },
    unlink: function(ids, callback, error_callback) {
        var self = this;
        _.each(ids, function (id) {
            self.get_cache(id).to_delete = true;
        });
        this.set_ids(_.difference(this.ids, _.pluck(_.filter(this.cache, function (c) {return c.to_delete;}), 'id')));
        this.trigger("dataset_changed", ids, callback, error_callback);
        return $.async_when({result: true}).done(callback);
    },
    reset_ids: function(ids, options) {
        var self = this;
        this.set_ids(ids);
        if (!options || !options.keep_read_data) {
            this.cache = {};
        } else {
            _.each(this.cache, function (cache) {
                self._update_cache(cache.id, {'changes': {}, 'to_delete': false});
            });
        }
        this.delete_all = false;
        this.cancel_read();
    },
    cancel_read: function () {
        _.invoke(_.clone(this.running_reads), 'reject');
    },
    read_ids: function (ids, fields, options) {
        // read what is necessary from the server to have ids and the given
        // fields in this.from_read
        var self = this;
        var to_get = _.filter(ids, function(id) {
            var cache = self.get_cache(id);
            return !cache.to_create && _.any(fields, function(x) {return cache.from_read[x] === undefined;});
        });
        options = options || {};

        var return_records = function() {
            var records = _.map(ids, function(id) {
                return _.clone(self.get_cache(id).values);
            });
            if (self.debug_mode) {
                if (_.include(records, undefined)) {
                    throw "Record not correctly loaded";
                }
            }
            var sort_fields = self._sort,
                    compare = function (v1, v2) {
                        return (v1 < v2) ? -1
                             : (v1 > v2) ? 1
                             : 0;
                    };
            // Array.sort is not necessarily stable. We must be careful with this because
            // sorting an array where all items are considered equal is a worst-case that
            // will randomize the array with an unstable sort! Therefore we must avoid
            // sorting if there are no sort_fields (i.e. all items are considered equal)
            // See also: http://ecma262-5.com/ELS5_Section_15.htm#Section_15.4.4.11 
            //           http://code.google.com/p/v8/issues/detail?id=90
            if (sort_fields.length) {
                records.sort(function (a, b) {
                    return _.reduce(sort_fields, function (acc, field) {
                        if (acc) { return acc; }
                        var sign = 1;
                        if (field[0] === '-') {
                            sign = -1;
                            field = field.slice(1);
                        }
                        if(!a[field] && a[field] !== 0){ return sign; }
                        if(!b[field] && b[field] !== 0){ return (sign == -1) ? 1 : -1; }
                        //m2o should be searched based on value[1] not based whole value(i.e. [id, value])
                        if(_.isArray(a[field]) && a[field].length == 2 && _.isString(a[field][1])){
                            return sign * compare(a[field][1], b[field][1]);
                        }
                        return sign * compare(a[field], b[field]);
                    }, 0);
                });
            }
            return $.when(records);
        };
        if(to_get.length > 0) {
            var def = $.Deferred();
            self.running_reads.push(def);
            def.always(function() {
                self.running_reads = _.without(self.running_reads, def);
            });
            var _super = this._super;
            this.mutex.exec(function () {
                if (def.state() !== "pending") return;
                _super.call(self, to_get, fields, options).then(_.bind(def.resolve, def), _.bind(def.reject, def));
                return def;
            });
            return def.then(function(records) {
                _.each(records, function(record, index) {
                    // add information into from_read
                    var id = to_get[index];
                    self._update_cache(id, _.extend(options, {'from_read': record}));
                });
                return return_records();
            });
        } else {
            return return_records();
        }
    },
    /**
     * Invalidates caching of a record in the dataset to ensure the next read
     * of that record will hit the server.
     *
     * Of use when an action is going to remote-alter a record which will then
     * need to be reloaded, e.g. action button.
     *
     * @param {Object} id record to remove from the BDS's cache
     */
    evict_record: function (id) {
        // Don't evict records which haven't yet been saved: there is no more
        // recent data on the server (and there potentially isn't any data),
        // and this breaks the assumptions of other methods (that the data
        // for new and altered records is both in the cache and in the change
        // or to_create collection)
        this.get_cache(id).from_read = {};
        this._update_cache(id);
    },
    call_button: function (method, args) {
        this.evict_record(args[0][0]);
        return this._super(method, args);
    },
    exec_workflow: function (id, signal) {
        this.evict_record(id);
        return this._super(id, signal);
    },
    alter_ids: function(n_ids, options) {
        var dirty = !_.isEqual(this.ids, n_ids);
        this._super(n_ids, options);
        if (dirty) {
            this.trigger("dataset_changed", n_ids, options);
        }
    },
});

BufferedDataSet.virtual_id_regex = /^one2many_v_id_.*$/;

var ProxyDataSet = DataSetSearch.extend({
    init: function() {
        this._super.apply(this, arguments);
        this.create_function = null;
        this.write_function = null;
        this.read_function = null;
        this.default_get_function = null;
        this.unlink_function = null;
    },
    read_ids: function (ids, fields, options) {
        if (this.read_function) {
            return this.read_function(ids, fields, options, this._super);
        } else {
            return this._super.apply(this, arguments);
        }
    },
    default_get: function(fields, options) {
        if (this.default_get_function) {
            return this.default_get_function(fields, options, this._super);
        } else {
            return this._super.apply(this, arguments);
        }
    },
    create: function(data, options) {
        if (this.create_function) {
            return this.create_function(data, options, this._super);
        } else {
            return this._super.apply(this, arguments);
        }
    },
    write: function (id, data, options) {
        if (this.write_function) {
            return this.write_function(id, data, options, this._super);
        } else {
            return this._super.apply(this, arguments);
        }
    },
    unlink: function(ids) {
        if (this.unlink_function) {
            return this.unlink_function(ids, this._super);
        } else {
            return this._super.apply(this, arguments);
        }
    },
});

var CompoundContext = Class.extend({
    init: function () {
        this.__ref = "compound_context";
        this.__contexts = [];
        this.__eval_context = null;
        var self = this;
        _.each(arguments, function(x) {
            self.add(x);
        });
    },
    add: function (context) {
        this.__contexts.push(context);
        return this;
    },
    set_eval_context: function (eval_context) {
        this.__eval_context = eval_context;
        return this;
    },
    get_eval_context: function () {
        return this.__eval_context;
    },
    eval: function() {
        return pyeval.eval('context', this, undefined, {no_user_context: true});
    },
});

var CompoundDomain = Class.extend({
    init: function () {
        this.__ref = "compound_domain";
        this.__domains = [];
        this.__eval_context = null;
        var self = this;
        _.each(arguments, function(x) {
            self.add(x);
        });
    },
    add: function(domain) {
        this.__domains.push(domain);
        return this;
    },
    set_eval_context: function(eval_context) {
        this.__eval_context = eval_context;
        return this;
    },
    get_eval_context: function() {
        return this.__eval_context;
    },
    eval: function() {
        return pyeval.eval('domain', this);
    },
});

function compute_domain (expr, fields) {
    if (! (expr instanceof Array))
        return !! expr;
    var stack = [];
    for (var i = expr.length - 1; i >= 0; i--) {
        var ex = expr[i];
        if (ex.length == 1) {
            var top = stack.pop();
            switch (ex) {
                case '|':
                    stack.push(stack.pop() || top);
                    continue;
                case '&':
                    stack.push(stack.pop() && top);
                    continue;
                case '!':
                    stack.push(!top);
                    continue;
                default:
                    throw new Error(_.str.sprintf(
                        _t("Unknown operator %s in domain %s"),
                        ex, JSON.stringify(expr)));
            }
        }

        var field = fields[ex[0]];
        if (!field) {
            throw new Error(_.str.sprintf(
                _t("Unknown field %s in domain %s"),
                ex[0], JSON.stringify(expr)));
        }
        var field_value = field.get_value ? field.get_value() : field.value;
        var op = ex[1];
        var val = ex[2];

        switch (op.toLowerCase()) {
            case '=':
            case '==':
                stack.push(_.isEqual(field_value, val));
                break;
            case '!=':
            case '<>':
                stack.push(!_.isEqual(field_value, val));
                break;
            case '<':
                stack.push(field_value < val);
                break;
            case '>':
                stack.push(field_value > val);
                break;
            case '<=':
                stack.push(field_value <= val);
                break;
            case '>=':
                stack.push(field_value >= val);
                break;
            case 'in':
                if (!_.isArray(val)) val = [val];
                stack.push(_(val).contains(field_value));
                break;
            case 'not in':
                if (!_.isArray(val)) val = [val];
                stack.push(!_(val).contains(field_value));
                break;
            default:
                console.warn(
                    _t("Unsupported operator %s in domain %s"),
                    op, JSON.stringify(expr));
        }
    }
    return _.all(stack, _.identity);
}


return {
    Query: Query,
    DataSet: DataSet,
    DataSetStatic: DataSetStatic,
    DataSetSearch: DataSetSearch,
    BufferedDataSet: BufferedDataSet,
    ProxyDataSet: ProxyDataSet,
    CompoundContext: CompoundContext,
    CompoundDomain: CompoundDomain,
    compute_domain: compute_domain,
};

});
