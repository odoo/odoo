
openerp.web.data = function(instance) {

/**
 * Serializes the sort criterion array of a dataset into a form which can be
 * consumed by OpenERP's RPC APIs.
 *
 * @param {Array} criterion array of fields, from first to last criteria, prefixed with '-' for reverse sorting
 * @returns {String} SQL-like sorting string (``ORDER BY``) clause
 */
instance.web.serialize_sort = function (criterion) {
    return _.map(criterion,
        function (criteria) {
            if (criteria[0] === '-') {
                return criteria.slice(1) + ' DESC';
            }
            return criteria + ' ASC';
        }).join(', ');
};

instance.web.Query = instance.web.Class.extend({
    init: function (model, fields) {
        this._model = model;
        this._fields = fields;
        this._filter = [];
        this._context = {};
        this._limit = false;
        this._offset = 0;
        this._order_by = [];
    },
    clone: function (to_set) {
        to_set = to_set || {};
        var q = new instance.web.Query(this._model, this._fields);
        q._context = this._context;
        q._filter = this._filter;
        q._limit = this._limit;
        q._offset = this._offset;
        q._order_by = this._order_by;

        for(var key in to_set) {
            if (!to_set.hasOwnProperty(key)) { continue; }
            switch(key) {
            case 'filter':
                q._filter = new instance.web.CompoundDomain(
                        q._filter, to_set.filter);
                break;
            case 'context':
                q._context = new instance.web.CompoundContext(
                        q._context, to_set.context);
                break;
            case 'limit':
            case 'offset':
            case 'order_by':
                q['_' + key] = to_set[key];
            }
        }
        return q;
    },
    _execute: function () {
        var self = this;
        return instance.session.rpc('/web/dataset/search_read', {
            model: this._model.name,
            fields: this._fields || false,
            domain: instance.web.pyeval.eval('domains',
                    [this._model.domain(this._filter)]),
            context: instance.web.pyeval.eval('contexts',
                    [this._model.context(this._context)]),
            offset: this._offset,
            limit: this._limit,
            sort: instance.web.serialize_sort(this._order_by)
        }).then(function (results) {
            self._count = results.length;
            return results.records;
        }, null);
    },
    /**
     * Fetches the first record matching the query, or null
     *
     * @returns {jQuery.Deferred<Object|null>}
     */
    first: function () {
        var self = this;
        return this.clone({limit: 1})._execute().then(function (records) {
            delete self._count;
            if (records.length) { return records[0]; }
            return null;
        });
    },
    /**
     * Fetches all records matching the query
     *
     * @returns {jQuery.Deferred<Array<>>}
     */
    all: function () {
        return this._execute();
    },
    /**
     * Fetches the number of records matching the query in the database
     *
     * @returns {jQuery.Deferred<Number>}
     */
    count: function () {
        if (this._count != undefined) { return $.when(this._count); }
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
        if (grouping === undefined) {
            return null;
        }

        if (!(grouping instanceof Array)) {
            grouping = _.toArray(arguments);
        }
        if (_.isEmpty(grouping)) { return null; }

        var self = this;

        var ctx = instance.web.pyeval.eval(
            'context', this._model.context(this._context));
        return this._model.call('read_group', {
            groupby: grouping,
            fields: _.uniq(grouping.concat(this._fields || [])),
            domain: this._model.domain(this._filter),
            context: this._model.context(this._context),
            offset: this._offset,
            limit: this._limit,
            orderby: instance.web.serialize_sort(this._order_by) || false
        }).then(function (results) {
            return _(results).map(function (result) {
                // FIX: querygroup initialization
                result.__context = result.__context || {};
                result.__context.group_by = result.__context.group_by || [];
                _.defaults(result.__context, ctx);
                return new instance.web.QueryGroup(
                    self._model.name, grouping[0], result);
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

instance.web.QueryGroup = instance.web.Class.extend({
    init: function (model, grouping_field, read_group_group) {
        // In cases where group_by_no_leaf and no group_by, the result of
        // read_group has aggregate fields but no __context or __domain.
        // Create default (empty) values for those so that things don't break
        var fixed_group = _.extend(
            {__context: {group_by: []}, __domain: []},
            read_group_group);

        var aggregates = {};
        _(fixed_group).each(function (value, key) {
            if (key.indexOf('__') === 0
                    || key === grouping_field
                    || key === grouping_field + '_count') {
                return;
            }
            aggregates[key] = value || 0;
        });

        this.model = new instance.web.Model(
            model, fixed_group.__context, fixed_group.__domain);

        var group_size = fixed_group[grouping_field + '_count'] || fixed_group.__count || 0;
        var leaf_group = fixed_group.__context.group_by.length === 0;
        this.attributes = {
            folded: !!(fixed_group.__fold),
            grouped_on: grouping_field,
            // if terminal group (or no group) and group_by_no_leaf => use group.__count
            length: group_size,
            value: fixed_group[grouping_field],
            // A group is open-able if it's not a leaf in group_by_no_leaf mode
            has_children: !(leaf_group && fixed_group.__context['group_by_no_leaf']),

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

instance.web.Model = instance.web.Class.extend({
    /**
     * @constructs instance.web.Model
     * @extends instance.web.Class
     *
     * @param {String} model_name name of the OpenERP model this object is bound to
     * @param {Object} [context]
     * @param {Array} [domain]
     */
    init: function (model_name, context, domain) {
        this.name = model_name;
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
     * Call a method (over RPC) on the bound OpenERP model.
     *
     * @param {String} method name of the method to call
     * @param {Array} [args] positional arguments
     * @param {Object} [kwargs] keyword arguments
     * @param {Object} [options] additional options for the rpc() method
     * @returns {jQuery.Deferred<>} call result
     */
    call: function (method, args, kwargs, options) {
        args = args || [];
        kwargs = kwargs || {};
        if (!_.isArray(args)) {
            // call(method, kwargs)
            kwargs = args;
            args = [];
        }
        instance.web.pyeval.ensure_evaluated(args, kwargs);
        var debug = instance.session.debug ? '/'+this.name+':'+method : '';
        return instance.session.rpc('/web/dataset/call_kw' + debug, {
            model: this.name,
            method: method,
            args: args,
            kwargs: kwargs
        }, options);
    },
    /**
     * Fetches a Query instance bound to this model, for searching
     *
     * @param {Array<String>} [fields] fields to ultimately fetch during the search
     * @returns {instance.web.Query}
     */
    query: function (fields) {
        return new instance.web.Query(this, fields);
    },
    /**
     * Executes a signal on the designated workflow, on the bound OpenERP model
     *
     * @param {Number} id workflow identifier
     * @param {String} signal signal to trigger on the workflow
     */
    exec_workflow: function (id, signal) {
        return instance.session.rpc('/web/dataset/exec_workflow', {
            model: this.name,
            id: id,
            signal: signal
        });
    },
    /**
     * Fetches the model's domain, combined with the provided domain if any
     *
     * @param {Array} [domain] to combine with the model's internal domain
     * @returns The model's internal domain, or the AND-ed union of the model's internal domain and the provided domain
     */
    domain: function (domain) {
        if (!domain) { return this._domain; }
        return new instance.web.CompoundDomain(
            this._domain, domain);
    },
    /**
     * Fetches the combination of the user's context and the domain context,
     * combined with the provided context if any
     *
     * @param {Object} [context] to combine with the model's internal context
     * @returns The union of the user's context and the model's internal context, as well as the provided context if any. In that order.
     */
    context: function (context) {
        return new instance.web.CompoundContext(
            instance.session.user_context, this._context, context || {});
    },
    /**
     * Button action caller, needs to perform cleanup if an action is returned
     * from the button (parsing of context and domain, and fixup of the views
     * collection for act_window actions)
     *
     * FIXME: remove when evaluator integrated
     */
    call_button: function (method, args) {
        instance.web.pyeval.ensure_evaluated(args, {});
        return instance.session.rpc('/web/dataset/call_button', {
            model: this.name,
            method: method,
            // Should not be necessary anymore. Integrate remote in this?
            domain_id: null,
            context_id: args.length - 1,
            args: args || []
        });
    },
});

instance.web.DataSet =  instance.web.Class.extend(instance.web.PropertiesMixin, {
    /**
     * Collection of OpenERP records, used to share records and the current selection between views.
     *
     * @constructs instance.web.DataSet
     *
     * @param {String} model the OpenERP model this dataset will manage
     */
    init: function(parent, model, context) {
        instance.web.PropertiesMixin.init.call(this);
        this.model = model;
        this.context = context || {};
        this.index = null;
        this._sort = [];
        this._model = new instance.web.Model(model, context);
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
     * @param {Array} fields fields to read and return, by default all fields are returned
     * @returns {$.Deferred}
     */
    read_ids: function (ids, fields, options) {
        options = options || {};
        // TODO: reorder results to match ids list
        return this._model.call('read',
            [ids, fields || false],
            {context: this._model.context(options.context)});
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
        return this._model.query(fields)
                .limit(options.limit || false)
                .offset(options.offset || 0)
                .all().done(function (records) {
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
     * @returns {$.Deferred}
     */
    create: function(data) {
        return this._model.call('create', [data], {context: this.get_context()});
    },
    /**
     * Saves the provided data in an existing db record
     *
     * @param {Number|String} id identifier for the record to alter
     * @param {Object} data field values to write into the record
     * @param {Function} callback function called with operation result
     * @param {Function} error_callback function called in case of write error
     * @returns {$.Deferred}
     */
    write: function (id, data, options) {
        options = options || {};
        return this._model.call('write', [[id], data], {context: this.get_context(options.context)}).done(this.trigger('dataset_changed', id, data, options));
    },
    /**
     * Deletes an existing record from the database
     *
     * @param {Number|String} ids identifier of the record to delete
     */
    unlink: function(ids) {
        return this._model.call('unlink', [ids], {context: this.get_context()}).done(this.trigger('dataset_changed', ids));
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
    name_create: function(name) {
        return this._model.call('name_create', [name], {context: this.get_context()});
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
            return instance.web.serialize_sort(this._sort);
        }
        var reverse = force_reverse || (this._sort[0] === field);
        this._sort.splice.apply(
            this._sort, [0, this._sort.length].concat(
                _.without(this._sort, field, '-' + field)));

        this._sort.unshift((reverse ? '-' : '') + field);
        return undefined;
    },
    size: function () {
        return this.ids.length;
    },
    alter_ids: function(n_ids) {
        this.ids = n_ids;
    },
    /**
     * Resequence records.
     *
     * @param {Array} ids identifiers of the records to resequence
     * @returns {$.Deferred}
     */
    resequence: function (ids, options) {
        options = options || {};
        return instance.session.rpc('/web/dataset/resequence', {
            model: this.model,
            ids: ids,
            context: instance.web.pyeval.eval(
                'context', this.get_context(options.context)),
        }).then(function (results) {
            return results;
        });
    },
});

instance.web.DataSetStatic =  instance.web.DataSet.extend({
    init: function(parent, model, context, ids) {
        var self = this;
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
        return this.read_ids(this.ids.slice(offset, end_pos), fields);
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

instance.web.DataSetSearch =  instance.web.DataSet.extend({
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
        this._model = new instance.web.Model(model, context, domain);
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
        this._model.domain(other_domain);
    },
    unlink: function(ids, callback, error_callback) {
        var self = this;
        return this._super(ids).done(function(result) {
            self.ids = _(self.ids).difference(ids);
            if (self._length) {
                self._length -= 1;
            }
            if (self.index !== null) {
                self.index = self.index <= self.ids.length - 1 ?
                    self.index : (self.ids.length > 0 ? self.ids.length -1 : 0);
            }
            self.trigger("dataset_changed", ids, callback, error_callback);
        });
    },
    size: function () {
        if (this._length !== undefined) {
            return this._length;
        }
        return this._super();
    }
});

instance.web.BufferedDataSet = instance.web.DataSetStatic.extend({
    virtual_id_prefix: "one2many_v_id_",
    debug_mode: true,
    init: function() {
        this._super.apply(this, arguments);
        this.reset_ids([]);
        this.last_default_get = {};
    },
    default_get: function(fields, options) {
        var self = this;
        return this._super(fields, options).done(function(res) {
            self.last_default_get = res;
        });
    },
    create: function(data) {
        var cached = {id:_.uniqueId(this.virtual_id_prefix), values: data,
            defaults: this.last_default_get};
        this.to_create.push(_.extend(_.clone(cached), {values: _.clone(cached.values)}));
        this.cache.push(cached);
        return $.Deferred().resolve(cached.id).promise();
    },
    write: function (id, data, options) {
        var self = this;
        var record = _.detect(this.to_create, function(x) {return x.id === id;});
        record = record || _.detect(this.to_write, function(x) {return x.id === id;});
        var dirty = false;
        if (record) {
            for (var k in data) {
                if (record.values[k] === undefined || record.values[k] !== data[k]) {
                    dirty = true;
                    break;
                }
            }
            $.extend(record.values, data);
        } else {
            dirty = true;
            record = {id: id, values: data};
            self.to_write.push(record);
        }
        var cached = _.detect(this.cache, function(x) {return x.id === id;});
        if (!cached) {
            cached = {id: id, values: {}};
            this.cache.push(cached);
        }
        $.extend(cached.values, record.values);
        if (dirty)
            this.trigger("dataset_changed", id, data, options);
        return $.Deferred().resolve(true).promise();
    },
    unlink: function(ids, callback, error_callback) {
        var self = this;
        _.each(ids, function(id) {
            if (! _.detect(self.to_create, function(x) { return x.id === id; })) {
                self.to_delete.push({id: id})
            }
        });
        this.to_create = _.reject(this.to_create, function(x) { return _.include(ids, x.id);});
        this.to_write = _.reject(this.to_write, function(x) { return _.include(ids, x.id);});
        this.cache = _.reject(this.cache, function(x) { return _.include(ids, x.id);});
        this.set_ids(_.without.apply(_, [this.ids].concat(ids)));
        this.trigger("dataset_changed", ids, callback, error_callback);
        return $.async_when({result: true}).done(callback);
    },
    reset_ids: function(ids) {
        this.set_ids(ids);
        this.to_delete = [];
        this.to_create = [];
        this.to_write = [];
        this.cache = [];
        this.delete_all = false;
    },
    read_ids: function (ids, fields, options) {
        var self = this;
        var to_get = [];
        _.each(ids, function(id) {
            var cached = _.detect(self.cache, function(x) {return x.id === id;});
            var created = _.detect(self.to_create, function(x) {return x.id === id;});
            if (created) {
                _.each(fields, function(x) {if (cached.values[x] === undefined)
                    cached.values[x] = created.defaults[x] || false;});
            } else {
                if (!cached || !_.all(fields, function(x) {return cached.values[x] !== undefined}))
                    to_get.push(id);
            }
        });
        var completion = $.Deferred();
        var return_records = function() {
            var records = _.map(ids, function(id) {
                return _.extend({}, _.detect(self.cache, function(c) {return c.id === id;}).values, {"id": id});
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
                        return sign * compare(a[field], b[field]);
                    }, 0);
                });
            }
            completion.resolve(records);
        };
        if(to_get.length > 0) {
            var rpc_promise = this._super(to_get, fields, options).done(function(records) {
                _.each(records, function(record, index) {
                    var id = to_get[index];
                    var cached = _.detect(self.cache, function(x) {return x.id === id;});
                    if (!cached) {
                        self.cache.push({id: id, values: record});
                    } else {
                        // I assume cache value is prioritary
                        cached.values = _.defaults(_.clone(cached.values), record);
                    }
                });
                return_records();
            });
            $.when(rpc_promise).fail(function() {completion.reject();});
        } else {
            return_records();
        }
        return completion.promise();
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
        for(var i=0, len=this.cache.length; i<len; ++i) {
            var record = this.cache[i];
            // if record we call the button upon is in the cache
            if (record.id === id) {
                // evict it so it gets reloaded from server
                this.cache.splice(i, 1);
                break;
            }
        }
    },
    call_button: function (method, args) {
        this.evict_record(args[0][0]);
        return this._super(method, args);
    },
    exec_workflow: function (id, signal) {
        this.evict_record(id);
        return this._super(id, signal);
    },
    alter_ids: function(n_ids) {
        this._super(n_ids);
        this.trigger("dataset_changed", n_ids);
    },
});
instance.web.BufferedDataSet.virtual_id_regex = /^one2many_v_id_.*$/;

instance.web.ProxyDataSet = instance.web.DataSetSearch.extend({
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
    create: function(data) {
        if (this.create_function) {
            return this.create_function(data, this._super);
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

instance.web.CompoundContext = instance.web.Class.extend({
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
    }
});

instance.web.CompoundDomain = instance.web.Class.extend({
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
    }
});

instance.web.DropMisordered = instance.web.Class.extend({
    /**
     * @constructs instance.web.DropMisordered
     * @extends instance.web.Class
     *
     * @param {Boolean} [failMisordered=false] whether mis-ordered responses should be failed or just ignored
     */
    init: function (failMisordered) {
        // local sequence number, for requests sent
        this.lsn = 0;
        // remote sequence number, seqnum of last received request
        this.rsn = -1;
        this.failMisordered = failMisordered || false;
    },
    /**
     * Adds a deferred (usually an async request) to the sequencer
     *
     * @param {$.Deferred} deferred to ensure add
     * @returns {$.Deferred}
     */
    add: function (deferred) {
        var res = $.Deferred();

        var self = this, seq = this.lsn++;
        deferred.done(function () {
            if (seq > self.rsn) {
                self.rsn = seq;
                res.resolve.apply(res, arguments);
            } else if (self.failMisordered) {
                res.reject();
            }
        }).fail(function () {
            res.reject.apply(res, arguments);
        });

        return res.promise();
    }
});

};

// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
