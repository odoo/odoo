
openerp.web.data = function(openerp) {

/**
 * Serializes the sort criterion array of a dataset into a form which can be
 * consumed by OpenERP's RPC APIs.
 *
 * @param {Array} criterion array of fields, from first to last criteria, prefixed with '-' for reverse sorting
 * @returns {String} SQL-like sorting string (``ORDER BY``) clause
 */
openerp.web.serialize_sort = function (criterion) {
    return _.map(criterion,
        function (criteria) {
            if (criteria[0] === '-') {
                return criteria.slice(1) + ' DESC';
            }
            return criteria + ' ASC';
        }).join(', ');
};

openerp.web.DataGroup =  openerp.web.Widget.extend( /** @lends openerp.web.DataGroup# */{
    /**
     * Management interface between views and grouped collections of OpenERP
     * records.
     *
     * The root DataGroup is instantiated with the relevant information
     * (a session, a model, a domain, a context and a group_by sequence), the
     * domain and context may be empty. It is then interacted with via
     * :js:func:`~openerp.web.DataGroup.list`, which is used to read the
     * content of the current grouping level.
     *
     * @constructs openerp.web.DataGroup
     * @extends openerp.web.Widget
     *
     * @param {openerp.web.Session} session Current OpenERP session
     * @param {String} model name of the model managed by this DataGroup
     * @param {Array} domain search domain for this DataGroup
     * @param {Object} context context of the DataGroup's searches
     * @param {Array} group_by sequence of fields by which to group
     * @param {Number} [level=0] nesting level of the group
     */
    init: function(parent, model, domain, context, group_by, level) {
        this._super(parent, null);
        if (group_by) {
            if (group_by.length || context['group_by_no_leaf']) {
                return new openerp.web.ContainerDataGroup( this, model, domain, context, group_by, level);
            } else {
                return new openerp.web.GrouplessDataGroup( this, model, domain, context, level);
            }
        }

        this.model = model;
        this.context = context;
        this.domain = domain;

        this.level = level || 0;
    },
    cls: 'DataGroup'
});
openerp.web.ContainerDataGroup = openerp.web.DataGroup.extend( /** @lends openerp.web.ContainerDataGroup# */ {
    /**
     *
     * @constructs openerp.web.ContainerDataGroup
     * @extends openerp.web.DataGroup
     *
     * @param session
     * @param model
     * @param domain
     * @param context
     * @param group_by
     * @param level
     */
    init: function (parent, model, domain, context, group_by, level) {
        this._super(parent, model, domain, context, null, level);

        this.group_by = group_by;
    },
    /**
     * The format returned by ``read_group`` is absolutely dreadful:
     *
     * * A ``__context`` key provides future grouping levels
     * * A ``__domain`` key provides the domain for the next search
     * * The current grouping value is provided through the name of the
     *   current grouping name e.g. if currently grouping on ``user_id``, then
     *   the ``user_id`` value for this group will be provided through the
     *   ``user_id`` key.
     * * Similarly, the number of items in the group (not necessarily direct)
     *   is provided via ``${current_field}_count``
     * * Other aggregate fields are just dumped there
     *
     * This function slightly improves the grouping records by:
     *
     * * Adding a ``grouped_on`` property providing the current grouping field
     * * Adding a ``value`` and a ``length`` properties which replace the
     *   ``$current_field`` and ``${current_field}_count`` ones
     * * Moving aggregate values into an ``aggregates`` property object
     *
     * Context and domain keys remain as-is, they should not be used externally
     * but in case they're needed...
     *
     * @param {Object} group ``read_group`` record
     */
    transform_group: function (group) {
        var field_name = this.group_by[0];
        // In cases where group_by_no_leaf and no group_by, the result of
        // read_group has aggregate fields but no __context or __domain.
        // Create default (empty) values for those so that things don't break
        var fixed_group = _.extend(
                {__context: {group_by: []}, __domain: []},
                group);

        var aggregates = {};
        _(fixed_group).each(function (value, key) {
            if (key.indexOf('__') === 0
                    || key === field_name
                    || key === field_name + '_count') {
                return;
            }
            aggregates[key] = value || 0;
        });

        return {
            __context: fixed_group.__context,
            __domain: fixed_group.__domain,

            grouped_on: field_name,
            // if terminal group (or no group) and group_by_no_leaf => use group.__count
            length: fixed_group[field_name + '_count'] || fixed_group.__count,
            value: fixed_group[field_name],

            openable: !(this.context['group_by_no_leaf']
                       && fixed_group.__context.group_by.length === 0),

            aggregates: aggregates
        };
    },
    fetch: function (fields) {
        // internal method
        var d = new $.Deferred();
        var self = this;

        this.rpc('/web/group/read', {
            model: this.model,
            context: this.context,
            domain: this.domain,
            fields: _.uniq(this.group_by.concat(fields)),
            group_by_fields: this.group_by,
            sort: openerp.web.serialize_sort(this.sort)
        }, function () { }).then(function (response) {
            var data_groups = _(response).map(
                    _.bind(self.transform_group, self));
            self.groups = data_groups;
            d.resolveWith(self, [data_groups]);
        }, function () {
            d.rejectWith.apply(d, [self, arguments]);
        });
        return d.promise();
    },
    /**
     * The items of a list have the following properties:
     *
     * ``length``
     *     the number of records contained in the group (and all of its
     *     sub-groups). This does *not* provide the size of the "next level"
     *     of the group, unless the group is terminal (no more groups within
     *     it).
     * ``grouped_on``
     *     the name of the field this level was grouped on, this is mostly
     *     used for display purposes, in order to know the name of the current
     *     level of grouping. The ``grouped_on`` should be the same for all
     *     objects of the list.
     * ``value``
     *     the value which led to this group (this is the value all contained
     *     records have for the current ``grouped_on`` field name).
     * ``aggregates``
     *     a mapping of other aggregation fields provided by ``read_group``
     *
     * @param {Array} fields the list of fields to aggregate in each group, can be empty
     * @param {Function} ifGroups function executed if any group is found (DataGroup.group_by is non-null and non-empty), called with a (potentially empty) list of groups as parameters.
     * @param {Function} ifRecords function executed if there is no grouping left to perform, called with a DataSet instance as parameter
     */
    list: function (fields, ifGroups, ifRecords) {
        var self = this;
        this.fetch(fields).then(function (group_records) {
            ifGroups(_(group_records).map(function (group) {
                var child_context = _.extend({}, self.context, group.__context);
                return _.extend(
                    new openerp.web.DataGroup(
                        self, self.model, group.__domain,
                        child_context, child_context.group_by,
                        self.level + 1),
                    group, {sort: self.sort});
            }));
        });
    }
});
openerp.web.GrouplessDataGroup = openerp.web.DataGroup.extend( /** @lends openerp.web.GrouplessDataGroup# */ {
    /**
     *
     * @constructs openerp.web.GrouplessDataGroup
     * @extends openerp.web.DataGroup
     *
     * @param session
     * @param model
     * @param domain
     * @param context
     * @param level
     */
    init: function (parent, model, domain, context, level) {
        this._super(parent, model, domain, context, null, level);
    },
    list: function (fields, ifGroups, ifRecords) {
        ifRecords(_.extend(
            new openerp.web.DataSetSearch(this, this.model),
            {domain: this.domain, context: this.context, _sort: this.sort}));
    }
});
openerp.web.StaticDataGroup = openerp.web.GrouplessDataGroup.extend( /** @lends openerp.web.StaticDataGroup# */ {
    /**
     * A specialization of groupless data groups, relying on a single static
     * dataset as its records provider.
     *
     * @constructs openerp.web.StaticDataGroup
     * @extends openerp.web.GrouplessDataGroup
     * @param {openep.web.DataSetStatic} dataset a static dataset backing the groups
     */
    init: function (dataset) {
        this.dataset = dataset;
    },
    list: function (fields, ifGroups, ifRecords) {
        ifRecords(this.dataset);
    }
});

openerp.web.DataSet =  openerp.web.Widget.extend( /** @lends openerp.web.DataSet# */{
    identifier_prefix: "dataset",
    /**
     * DateaManagement interface between views and the collection of selected
     * OpenERP records (represents the view's state?)
     *
     * @constructs openerp.web.DataSet
     * @extends openerp.web.Widget
     *
     * @param {String} model the OpenERP model this dataset will manage
     */
    init: function(parent, model, context) {
        this._super(parent);
        this.model = model;
        this.context = context || {};
        this.index = null;
    },
    previous: function () {
        this.index -= 1;
        if (this.index < 0) {
            this.index = this.ids.length - 1;
        }
        return this;
    },
    next: function () {
        this.index += 1;
        if (this.index >= this.ids.length) {
            this.index = 0;
        }
        return this;
    },
    /**
     * Read records.
     *
     * @param {Array} ids identifiers of the records to read
     * @param {Array} fields fields to read and return, by default all fields are returned
     * @param {Function} callback function called with read result
     * @returns {$.Deferred}
     */
    read_ids: function (ids, fields, callback) {
        return this.rpc('/web/dataset/get', {
            model: this.model,
            ids: ids,
            fields: fields,
            context: this.get_context()
        }, callback);
    },
    /**
     * Read a slice of the records represented by this DataSet, based on its
     * domain and context.
     *
     * @param {Array} [fields] fields to read and return, by default all fields are returned
     * @params {Object} options
     * @param {Number} [options.offset=0] The index from which selected records should be returned
     * @param {Number} [options.limit=null] The maximum number of records to return
     * @param {Function} callback function called with read_slice result
     * @returns {$.Deferred}
     */
    read_slice: function (fields, options, callback) { 
        return null; 
    },
    /**
     * Reads the current dataset record (from its index)
     *
     * @params {Array} [fields] fields to read and return, by default all fields are returned
     * @params {Function} callback function called with read_index result
     * @returns {$.Deferred}
     */
    read_index: function (fields, callback) {
        var def = $.Deferred().then(callback);
        if (_.isEmpty(this.ids)) {
            def.reject();
        } else {
            fields = fields || false;
            return this.read_ids([this.ids[this.index]], fields).then(function(records) {
                def.resolve(records[0]);
            }, function() {
                def.reject.apply(def, arguments);
            });
        }
        return def.promise();
    },
    /**
     * Reads default values for the current model
     *
     * @param {Array} [fields] fields to get default values for, by default all defaults are read
     * @param {Function} callback function called with default_get result
     * @returns {$.Deferred}
     */
    default_get: function(fields, callback) {
        return this.rpc('/web/dataset/default_get', {
            model: this.model,
            fields: fields,
            context: this.get_context()
        }, callback);
    },
    /**
     * Creates a new record in db
     *
     * @param {Object} data field values to set on the new record
     * @param {Function} callback function called with operation result
     * @param {Function} error_callback function called in case of creation error
     * @returns {$.Deferred}
     */
    create: function(data, callback, error_callback) {
        return this.rpc('/web/dataset/create', {
            model: this.model,
            data: data,
            context: this.get_context()
        }, callback, error_callback);
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
    write: function (id, data, options, callback, error_callback) {
        options = options || {};
        return this.rpc('/web/dataset/save', {
            model: this.model,
            id: id,
            data: data,
            context: this.get_context(options.context)
        }, callback, error_callback);
    },
    /**
     * Deletes an existing record from the database
     *
     * @param {Number|String} ids identifier of the record to delete
     * @param {Function} callback function called with operation result
     * @param {Function} error_callback function called in case of deletion error
     */
    unlink: function(ids, callback, error_callback) {
        var self = this;
        return this.call_and_eval("unlink", [ids, this.get_context()], null, 1,
            callback, error_callback);
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
    call: function (method, args, callback, error_callback) {
        return this.rpc('/web/dataset/call', {
            model: this.model,
            method: method,
            args: args || []
        }, callback, error_callback);
    },
    /**
     * Calls an arbitrary method, with more crazy
     *
     * @param {String} method
     * @param {Array} [args]
     * @param {Number} [domain_index] index of a domain to evaluate in the args array
     * @param {Number} [context_index] index of a context to evaluate in the args array
     * @param {Function} callback
     * @param {Function }error_callback
     * @returns {$.Deferred}
     */
    call_and_eval: function (method, args, domain_index, context_index, callback, error_callback) {
        return this.rpc('/web/dataset/call', {
            model: this.model,
            method: method,
            domain_id: domain_index || null,
            context_id: context_index || null,
            args: args || []
        }, callback, error_callback);
    },
    /**
     * Calls a button method, usually returning some sort of action
     *
     * @param {String} method
     * @param {Array} [args]
     * @param {Function} callback
     * @param {Function} error_callback
     * @returns {$.Deferred}
     */
    call_button: function (method, args, callback, error_callback) {
        return this.rpc('/web/dataset/call_button', {
            model: this.model,
            method: method,
            domain_id: null,
            context_id: 1,
            args: args || []
        }, callback, error_callback);
    },
    /**
     * Fetches the "readable name" for records, based on intrinsic rules
     *
     * @param {Array} ids
     * @param {Function} callback
     * @returns {$.Deferred}
     */
    name_get: function(ids, callback) {
        return this.call_and_eval('name_get', [ids, this.get_context()], null, 1, callback);
    },
    /**
     * 
     * @param {String} name name to perform a search for/on
     * @param {Array} [domain=[]] filters for the objects returned, OpenERP domain
     * @param {String} [operator='ilike'] matching operator to use with the provided name value
     * @param {Number} [limit=100] maximum number of matches to return
     * @param {Function} callback function to call with name_search result
     * @returns {$.Deferred}
     */
    name_search: function (name, domain, operator, limit, callback) {
        return this.call_and_eval('name_search',
            [name || '', domain || false, operator || 'ilike', this.get_context(), limit || 100],
            1, 3, callback);
    },
    /**
     * @param name
     * @param callback
     */
    name_create: function(name, callback) {
        return this.call_and_eval('name_create', [name, this.get_context()], null, 1, callback);
    },
    exec_workflow: function (id, signal, callback) {
        return this.rpc('/web/dataset/exec_workflow', {
            model: this.model,
            id: id,
            signal: signal
        }, callback);
    },
    get_context: function(request_context) {
        if (request_context) {
            return new openerp.web.CompoundContext(this.context, request_context);
        }
        return this.context;
    }
});
openerp.web.DataSetStatic =  openerp.web.DataSet.extend({
    init: function(parent, model, context, ids) {
        this._super(parent, model, context);
        // all local records
        this.ids = ids || [];
    },
    read_slice: function (fields, options, callback) {
        // TODO remove fields from options
        var self = this,
            offset = options.offset || 0,
            limit = options.limit || false,
            fields = fields || false;
        var end_pos = limit && limit !== -1 ? offset + limit : undefined;
        return this.read_ids(this.ids.slice(offset, end_pos), fields, callback);
    },
    set_ids: function (ids) {
        this.ids = ids;
        if (this.index !== null) {
            this.index = this.index <= this.ids.length - 1 ?
                this.index : (this.ids.length > 0 ? this.length - 1 : 0);
        }
    },
    unlink: function(ids) {
        this.on_unlink(ids);
        return $.Deferred().resolve({result: true});
    },
    on_unlink: function(ids) {
        this.set_ids(_.without.apply(null, [this.ids].concat(ids)));
    }
});
openerp.web.DataSetSearch =  openerp.web.DataSet.extend(/** @lends openerp.web.DataSetSearch */{
    /**
     * @constructs openerp.web.DataSetSearch
     * @extends openerp.web.DataSet
     *
     * @param {Object} parent
     * @param {String} model
     * @param {Object} context
     * @param {Array} domain
     */
    init: function(parent, model, context, domain) {
        this._super(parent, model, context);
        this.domain = domain || [];
        this._sort = [];
        this.offset = 0;
        // subset records[offset:offset+limit]
        // is it necessary ?
        this.ids = [];
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
     * @param {Function} callback function called with read_slice result
     * @returns {$.Deferred}
     */
    read_slice: function (fields, options, callback) {
        var self = this;
        var options = options || {};
        var offset = options.offset || 0;
        return this.rpc('/web/dataset/search_read', {
            model: this.model,
            fields: fields || false,
            domain: this.get_domain(options.domain),
            context: this.get_context(options.context),
            sort: this.sort(),
            offset: offset,
            limit: options.limit || false
        }).pipe(function (result) {
            self.ids = result.ids;
            self.offset = offset;
            return result.records;
        }).then(callback);
    },
    get_domain: function (other_domain) {
        if (other_domain) {
            return new openerp.web.CompoundDomain(this.domain, other_domain);
        }
        return this.domain;
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
            return openerp.web.serialize_sort(this._sort);
        }
        var reverse = force_reverse || (this._sort[0] === field);
        this._sort.splice.apply(
            this._sort, [0, this._sort.length].concat(
                _.without(this._sort, field, '-' + field)));

        this._sort.unshift((reverse ? '-' : '') + field);
        return undefined;
    },
    unlink: function(ids, callback, error_callback) {
        var self = this;
        return this._super(ids, function(result) {
            self.ids = _.without.apply(_, [self.ids].concat(ids));
            if (this.index !== null) {
                self.index = self.index <= self.ids.length - 1 ?
                    self.index : (self.ids.length > 0 ? self.ids.length -1 : 0);
            }
            if (callback)
                callback(result);
        }, error_callback);
    }
});
openerp.web.BufferedDataSet = openerp.web.DataSetStatic.extend({
    virtual_id_prefix: "one2many_v_id_",
    debug_mode: true,
    init: function() {
        this._super.apply(this, arguments);
        this.reset_ids([]);
        this.last_default_get = {};
    },
    default_get: function(fields, callback) {
        return this._super(fields).then(this.on_default_get).then(callback);
    },
    on_default_get: function(res) {
        this.last_default_get = res;
    },
    /**
     * Makes sure this dataset has the fields_get for its model stored locally,
     * so create/write methods are able to determine if written fields are m2os
     * and can name_get those fields if that's the case (in order to cache a
     * correct m2o value for them)
     *
     * @returns {$.Deferred} whether the fields_get is done executing, provides the fields_get value to its callbacks
     */
    ensure_has_fields: function () {
        var self = this;

        if (this.fields_get) {
            var d = $.Deferred();
            setTimeout(function () { d.resolve(self.fields_get, true); }, 0);
            return d.promise();
        } else {
            return self.call('fields_get', [], function (fields_get) {
                self.fields_get = fields_get;
            });
        }
    },
    /**
     * Relational fields may not be written in the same format they are read.
     *
     * Since the BufferedDataSet is a bit dumb, it returns what it's got stored
     * in its cache, which for modified value is what it was given. This breaks
     * some basic contracts of openerp such as m2o read being in the
     * ``name_get`` format.
     *
     * Because create & write are supposed to be asynchronous, though, it
     * should be easy to just name_get all incorrect values.
     *
     * @param {Object} data form-data to write to the cache
     * @returns {$.Deferred} resolved with a fixed data dictionary
     */
    fix_relational: function (data) {
        var self = this;
        var results = $.Deferred();
        this.ensure_has_fields().then(function (fields) {
            var fields_to_fix = _(fields).chain()
                .map(function (d, k) { return {key: k, descriptor: d}; })
                .filter(function (field) {
                    // keep m2o fields which are in the data dict
                    return field.descriptor.type === 'many2one' &&
                           field.key in data;
                }).pluck('key')
                .value();
            var name_gets = _(fields_to_fix).map(function (field) {
                return new openerp.web.DataSet(self, self.fields_get[field].relation)
                    .name_get([data[field]], null);
            });
            $.when.apply(null, name_gets).then(function () {
                var record = _.extend({}, data);
                for(var i=0; i<fields_to_fix.length; ++i) {
                    record[fields_to_fix[i]] = arguments[i][0];
                }
                results.resolve(record);
            });
        });
        return results;
    },
    create: function(data, callback, error_callback) {
        var self = this;
        var prom = $.Deferred().then(callback);
        this.fix_relational(data).then(function (fixed_data) {
            var cached = {
                id:_.uniqueId(self.virtual_id_prefix),
                values: fixed_data,
                defaults: self.last_default_get
            };
            this.to_create.push(_.extend(_.clone(cached), {
                values: _.clone(cached.values)}));
            self.cache.push(cached);
            self.on_change();
            prom.resolve({result: cached.id});
        });
        return prom.promise();
    },
    write: function (id, data, options, callback) {
        var self = this;
        var to_return = $.Deferred().then(callback);
        this.fix_relational(data).then(function (fixed_data) {
            var record = _.detect(self.to_create, function(x) {return x.id === id;});
            record = record || _.detect(self.to_write, function(x) {return x.id === id;});
            var dirty = false;
            if (record) {
                for (var k in fixed_data) {
                    if (record.values[k] === undefined || record.values[k] !== fixed_data[k]) {
                        dirty = true;
                        break;
                    }
                }
                $.extend(record.values, fixed_data);
            } else {
                dirty = true;
                record = {id: id, values: fixed_data};
                self.to_write.push(record);
            }
            var cached = _.detect(self.cache, function(x) {return x.id === id;});
            if (!cached) {
                cached = {id: id, values: {}};
                this.cache.push(cached);
            }
            $.extend(cached.values, record.values);
            if (dirty)
                self.on_change();
            to_return.resolve({result: true});
        });
        return to_return.promise();
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
        this.on_change();
        var to_return = $.Deferred().then(callback);
        setTimeout(function () {to_return.resolve({result: true});}, 0);
        return to_return.promise();
    },
    reset_ids: function(ids) {
        this.set_ids(ids);
        this.to_delete = [];
        this.to_create = [];
        this.to_write = [];
        this.cache = [];
        this.delete_all = false;
    },
    on_change: function() {},
    read_ids: function (ids, fields, callback) {
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
        var completion = $.Deferred().then(callback);
        var return_records = function() {
            var records = _.map(ids, function(id) {
                return _.extend({}, _.detect(self.cache, function(c) {return c.id === id;}).values, {"id": id});
            });
            if (self.debug_mode) {
                if (_.include(records, undefined)) {
                    throw "Record not correctly loaded";
                }
            }
            completion.resolve(records);
        };
        if(to_get.length > 0) {
            var rpc_promise = this._super(to_get, fields, function(records) {
                _.each(records, function(record, index) {
                    var id = to_get[index];
                    var cached = _.detect(self.cache, function(x) {return x.id === id;});
                    if (!cached) {
                        self.cache.push({id: id, values: record});
                    } else {
                        // I assume cache value is prioritary
                        _.defaults(cached.values, record);
                    }
                });
                return_records();
            });
            $.when(rpc_promise).fail(function() {completion.reject();});
        } else {
            return_records();
        }
        return completion.promise();
    }
});
openerp.web.BufferedDataSet.virtual_id_regex = /^one2many_v_id_.*$/;

openerp.web.ProxyDataSet = openerp.web.DataSetSearch.extend({
    init: function() {
        this._super.apply(this, arguments);
        this.create_function = null;
        this.write_function = null;
        this.read_function = null;
    },
    read_ids: function () {
        if (this.read_function) {
            return this.read_function.apply(null, arguments);
        } else {
            return this._super.apply(this, arguments);
        }
    },
    default_get: function(fields, callback) {
        return this._super(fields, callback).then(this.on_default_get);
    },
    on_default_get: function(result) {},
    create: function(data, callback, error_callback) {
        this.on_create(data);
        if (this.create_function) {
            return this.create_function(data, callback, error_callback);
        } else {
            console.warn("trying to create a record using default proxy dataset behavior");
            var to_return = $.Deferred().then(callback);
            setTimeout(function () {to_return.resolve({"result": undefined});}, 0);
            return to_return.promise();
        }
    },
    on_create: function(data) {},
    write: function (id, data, options, callback) {
        this.on_write(id, data);
        if (this.write_function) {
            return this.write_function(id, data, options, callback);
        } else {
            console.warn("trying to write a record using default proxy dataset behavior");
            var to_return = $.Deferred().then(callback);
            setTimeout(function () {to_return.resolve({"result": true});}, 0);
            return to_return.promise();
        }
    },
    on_write: function(id, data) {},
    unlink: function(ids, callback, error_callback) {
        this.on_unlink(ids);
        console.warn("trying to unlink a record using default proxy dataset behavior");
        var to_return = $.Deferred().then(callback);
        setTimeout(function () {to_return.resolve({"result": true});}, 0);
        return to_return.promise();
    },
    on_unlink: function(ids) {}
});

openerp.web.Model = openerp.web.SessionAware.extend({
    init: function(session, model_name) {
        this._super(session);
        this.model_name = model_name;
    },
    get_func: function(method_name) {
        var self = this;
        return function() {
            if (method_name == "search_read")
                return self._search_read.apply(self, arguments);
            return self._call(method_name, _.toArray(arguments));
        };
    },
    _call: function (method, args) {
        return this.rpc('/web/dataset/call', {
            model: this.model_name,
            method: method,
            args: args
        }).pipe(function(result) {
            if (method == "read" && result instanceof Array && result.length > 0 && result[0]["id"]) {
                var index = {};
                _.each(_.range(result.length), function(i) {
                    index[result[i]["id"]] = result[i];
                })
                result = _.map(args[0], function(x) {return index[x];});
            }
            return result;
        });
    },
    _search_read: function(domain, fields, offset, limit, order, context) {
        return this.rpc('/web/dataset/search_read', {
            model: this.model_name,
            fields: fields,
            offset: offset,
            limit: limit,
            domain: domain,
            sort: order,
            context: context
        }).pipe(function(result) {
            return result.records;
        });;
    }
});

openerp.web.CompoundContext = openerp.web.Class.extend({
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

openerp.web.CompoundDomain = openerp.web.Class.extend({
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
};

// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
