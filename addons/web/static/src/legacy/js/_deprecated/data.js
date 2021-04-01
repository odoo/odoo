odoo.define('web.data', function (require) {
"use strict";

var Class = require('web.Class');
var Context = require('web.Context');
var concurrency = require('web.concurrency');
var mixins = require('web.mixins');
var session = require('web.session');
var translation = require('web.translation');
var pyUtils = require('web.py_utils');

var _t = translation._t;

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
                q._filter = (q._filter || []).concat(to_set.filter || []);
                break;
            case 'context':
                q._context = new Context(
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
            domain: pyUtils.eval('domains',
                    [this._model.domain(this._filter)]),
            context: pyUtils.eval('contexts',
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
     * @returns {Promise<Object|null>}
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
     * @returns {Promise<Array<>>}
     */
    all: function (options) {
        return this._execute(options);
    },
    /**
     * Fetches the number of records matching the query in the database
     *
     * @returns {Promise<Number>}
     */
    count: function () {
        if (this._count !== undefined) { return Promise.resolve(this._count); }
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
        var ctx = pyUtils.eval(
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
        for (var key in fixed_group) {
            if (fixed_group.hasOwnProperty(key)) {
                if (!(key.indexOf('__') === 0
                    || _.contains(grouping_fields, key)
                    || (key === count_key))) {
                    aggregates[key] = fixed_group[key] || 0;
                }
            }
        }

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
    init: function (parent, model, context) {
        mixins.PropertiesMixin.init.call(this);
        this.setParent(parent);
        this.model = model;
        this.context = context || {};
        this.index = null;
        this._sort = [];
        this._model = new Model(model, context);
        this.orderer = new concurrency.DropMisordered();
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
    select_id: function (id) {
        var idx = this.get_id_index(id);
        if (idx === null) {
            return false;
        } else {
            this.index = idx;
            return true;
        }
    },
    get_id_index: function (id) {
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
     * @returns {Promise}
     */
    read_ids: function (ids, fields, options) {
        if (_.isEmpty(ids)) {
            return Promise.resolve([]);
        }

        options = options || {};
        var method = 'read';
        var ids_arg = ids;
        var context = this.get_context(options.context);
        if (options.check_access_rule === true){
            method = 'search_read';
            ids_arg = [['id', 'in', ids]];
            context = new Context(context, {active_test: false});
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
     * @returns {Promise}
     */
    read_slice: function (fields, options) {
        var self = this;
        options = options || {};
        var query = this._model.query(fields)
                .limit(options.limit || false)
                .offset(options.offset || 0)
                .all();
        var prom = this.orderer.add(query);
        prom.then(function (records) {
            self.ids = _(records).pluck('id');
        });
        return prom;
    },
    /**
     * Reads the current dataset record (from its index)
     *
     * @params {Array} [fields] fields to read and return, by default all fields are returned
     * @param {Object} [options.context] context data to add to the request payload, on top of the DataSet's own context
     * @returns {Promise}
     */
    read_index: function (fields, options) {
        options = options || {};
        return this.read_ids([this.ids[this.index]], fields, options).then(function (records) {
            if (_.isEmpty(records)) { return Promise.reject(); }
            return records[0];
        });
    },
    /**
     * Reads default values for the current model
     *
     * @param {Array} [fields] fields to get default values for, by default all defaults are read
     * @param {Object} [options.context] context data to add to the request payload, on top of the DataSet's own context
     * @returns {Promise}
     */
    default_get: function (fields, options) {
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
     * @returns {Promise}
     */
    create: function (data, options) {
        var self = this;
        var prom = this._model.call('create', [data], {
            context: this.get_context()
        });
        prom.then(function () {
            self.trigger('dataset_changed', data, options);
        });
        return prom;
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
     * @returns {Promise}
     */
    write: function (id, data, options) {
        options = options || {};
        var self = this;
        var prom = this._model.call('write', [[id], data], {
            context: this.get_context(options.context)
        });
        prom.then(function () {
            self.trigger('dataset_changed', id, data, options);
        });
        return prom;
    },
    /**
     * Deletes an existing record from the database
     *
     * @param {Number|String} ids identifier of the record to delete
     */
    unlink: function (ids) {
        var self = this;
        var prom = this._model.call('unlink', [ids], {
            context: this.get_context()
        });
        prom.then(function () {
            self.trigger('dataset_changed', ids);
        });
        return prom;
    },
    /**
     * Calls an arbitrary RPC method
     *
     * @param {String} method name of the method (on the current model) to call
     * @param {Array} [args] arguments to pass to the method
     * @param {Function} callback
     * @param {Function} error_callback
     * @returns {Promise}
     */
    call: function (method, args) {
        return this._model.call(method, args);
    },
    /**
     * Calls a button method, usually returning some sort of action
     *
     * @param {String} method
     * @param {Array} [args]
     * @returns {Promise}
     */
    call_button: function (method, args) {
        return this._model.call_button(method, args);
    },
    /**
     * Fetches the "readable name" for records, based on intrinsic rules
     *
     * @param {Array} ids
     * @returns {Promise}
     */
    name_get: function (ids) {
        return this._model.call('name_get', [ids], {context: this.get_context()});
    },
    /**
     *
     * @param {String} name name to perform a search for/on
     * @param {Array} [domain=[]] filters for the objects returned, OpenERP domain
     * @param {String} [operator='ilike'] matching operator to use with the provided name value
     * @param {Number} [limit=0] maximum number of matches to return
     * @param {Function} callback function to call with name_search result
     * @returns {Promise}
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
    name_create: function (name, context) {
        return this._model.call('name_create', [name], {context: this.get_context(context)});
    },
    get_context: function (request_context) {
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
    alter_ids: function (n_ids) {
        this.ids = n_ids;
    },
    remove_ids: function (ids) {
        this.alter_ids(_(this.ids).difference(ids));
    },
    add_ids: function (ids, at) {
        var args = [at, 0].concat(_.difference(ids, this.ids));
        this.ids.splice.apply(this.ids, args);
    },
    /**
     * Resequence records.
     *
     * @param {Array} ids identifiers of the records to resequence
     * @returns {Promise}
     */
    resequence: function (ids, options) {
        options = options || {};
        return session.rpc('/web/dataset/resequence', {
            model: this.model,
            ids: ids,
            context: pyUtils.eval(
                'context', this.get_context(options.context)),
        }).then(function (results) {
            return results;
        });
    },
});

var DataSetStatic =  DataSet.extend({
    init: function (parent, model, context, ids) {
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
    unlink: function (ids) {
        this.set_ids(_.without.apply(null, [this.ids].concat(ids)));
        this.trigger('unlink', ids);
        return Promise.resolve({result: true});
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
    init: function (parent, model, context, domain) {
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
     * @returns {Promise}
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

        var prom = this.orderer.add(q.all());
        prom.then(function (records) {
            // FIXME: not sure about that one, *could* have discarded count
            q.count().then(function (count) { self._length = count; });
            self.ids = _(records).pluck('id');
        });
        return prom;
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
    add_ids: function (ids, at) {
        var before = this.ids.length;
        this._super(ids, at);
        if(this._length){
            this._length += (this.ids.length - before);
        }
    },
    unlink: function (ids, callback, error_callback) {
        var self = this;
        var prom = this._super(ids);
        prom.then(function () {
            self.remove_ids( ids);
            self.trigger("dataset_changed", ids, callback, error_callback);
        });
        return prom;
    },
    size: function () {
        if (this._length !== null) {
            return this._length;
        }
        return this._super();
    }
});

var data = {
    Query: Query,
    DataSet: DataSet,
    DataSetStatic: DataSetStatic,
    DataSetSearch: DataSetSearch,
    /** @type String */
    noDisplayContent: "<em class=\"text-warning\">" + _t("Unnamed") + "</em>",
};


var Model = Class.extend({
    /**
    new openerp.web.Model(name[, context[, domain]])

    @constructs instance.web.Model
    @extends instance.web.Class

    @param {String} name name of the OpenERP model this object is bound to
    @param {Object} [context]
    @param {Array} [domain]
    */
    init: function(name, context, domain) {
        this.name = name;
        this._context = context || {};
        this._domain = domain || [];
    },
    /**
     * @deprecated does not allow to specify kwargs, directly use call() instead
     */
    get_func: function (method_name) {
        var self = this;
        return function () {
            return self.call(method_name, _.toArray(arguments));
        };
    },
    /**
     * Fetches a Query instance bound to this model, for searching
     *
     * @param {Array<String>} [fields] fields to ultimately fetch during the search
     * @returns {instance.web.Query}
     */
    query: function (fields) {
        return new data.Query(this, fields);
    },
    /**
     * Fetches the model's domain, combined with the provided domain if any
     *
     * @param {Array} [domain] to combine with the model's internal domain
     * @returns {Array} The model's internal domain, or the AND-ed union of the model's internal domain and the provided domain
     */
    domain: function (domain) {
        if (!domain) { return this._domain; }
        return this._domain.concat(domain);
    },
    /**
     * Fetches the combination of the user's context and the domain context,
     * combined with the provided context if any
     *
     * @param {Object} [context] to combine with the model's internal context
     * @returns {web.Context} The union of the user's context and the model's internal context, as well as the provided context if any. In that order.
     */
    context: function (context) {
        return new Context(session.user_context, this._context, context || {});
    },
    /**
     * Call a method (over RPC) on the bound OpenERP model.
     *
     * @param {String} method name of the method to call
     * @param {Array} [args] positipyEvalonal arguments
     * @param {Object} [kwargs] keyword arguments
     * @param {Object} [options] additional options for the rpc() method
     * @returns {Promise<>} call result
     */
    call: function (method, args, kwargs, options) {
        args = args || [];
        kwargs = kwargs || {};
        if (!_.isArray(args)) {
            // call(method, kwargs)
            kwargs = args;
            args = [];
        }
        pyUtils.ensure_evaluated(args, kwargs);
        var call_kw = '/web/dataset/call_kw/' + this.name + '/' + method;
        return session.rpc(call_kw, {
            model: this.name,
            method: method,
            args: args,
            kwargs: kwargs
        }, options);
    },
    call_button: function (method, args) {
        pyUtils.ensure_evaluated(args, {});
        // context should be the last argument
        var context = (args || []).length > 0 ? args.pop() : {};
        return session.rpc('/web/dataset/call_button', {
            model: this.name,
            method: method,
            args: args || [],
            kwargs: {context: context},
        });
    },
});


return data;

});
