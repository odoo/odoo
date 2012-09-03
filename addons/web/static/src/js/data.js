
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

openerp.web.DataGroup =  openerp.web.OldWidget.extend( /** @lends openerp.web.DataGroup# */{
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
     * @extends openerp.web.OldWidget
     *
     * @param {openerp.web.OldWidget} parent widget
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

        var group_size = fixed_group[field_name + '_count'] || fixed_group.__count || 0;
        var leaf_group = fixed_group.__context.group_by.length === 0;
        return {
            __context: fixed_group.__context,
            __domain: fixed_group.__domain,

            grouped_on: field_name,
            // if terminal group (or no group) and group_by_no_leaf => use group.__count
            length: group_size,
            value: fixed_group[field_name],
            // A group is openable if it's not a leaf in group_by_no_leaf mode
            openable: !(leaf_group && this.context['group_by_no_leaf']),

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

openerp.web.DataSet =  openerp.web.OldWidget.extend( /** @lends openerp.web.DataSet# */{
    /**
     * DateaManagement interface between views and the collection of selected
     * OpenERP records (represents the view's state?)
     *
     * @constructs openerp.web.DataSet
     * @extends openerp.web.OldWidget
     *
     * @param {String} model the OpenERP model this dataset will manage
     */
    init: function(parent, model, context) {
        this._super(parent);
        this.model = model;
        this.context = context || {};
        this.index = null;
        this._sort = [];
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
        var options = options || {};
        return this.rpc('/web/dataset/get', {
            model: this.model,
            ids: ids,
            fields: fields,
            context: this.get_context(options.context)
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
        return null;
    },
    /**
     * Reads the current dataset record (from its index)
     *
     * @params {Array} [fields] fields to read and return, by default all fields are returned
     * @param {Object} [options.context] context data to add to the request payload, on top of the DataSet's own context
     * @returns {$.Deferred}
     */
    read_index: function (fields, options) {
        var def = $.Deferred();
        if (_.isEmpty(this.ids)) {
            def.reject();
        } else {
            fields = fields || false;
            this.read_ids([this.ids[this.index]], fields, options).then(function(records) {
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
     * @param {Object} [options.context] context data to add to the request payload, on top of the DataSet's own context
     * @returns {$.Deferred}
     */
    default_get: function(fields, options) {
        var options = options || {};
        return this.rpc('/web/dataset/default_get', {
            model: this.model,
            fields: fields,
            context: this.get_context(options.context)
        });
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
     * @param {Function} error_callback
     * @returns {$.Deferred}
     */
    call_and_eval: function (method, args, domain_index, context_index, callback, error_callback) {
        return this.rpc('/web/dataset/call', {
            model: this.model,
            method: method,
            domain_id: domain_index == undefined ? null : domain_index,
            context_id: context_index == undefined ? null : context_index,
            args: args || [],
            // FIXME: API which does not suck for aborting requests in-flight
            aborter: this
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
            context_id: args.length - 1,
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
     * @param {Number} [limit=0] maximum number of matches to return
     * @param {Function} callback function to call with name_search result
     * @returns {$.Deferred}
     */
    name_search: function (name, domain, operator, limit, callback) {
        return this.call_and_eval('name_search',
            [name || '', domain || false, operator || 'ilike', this.get_context(), limit || 0],
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
    size: function () {
        return this.ids.length;
    },
    alter_ids: function(n_ids) {
    	this.ids = n_ids;
    },
});
openerp.web.DataSetStatic =  openerp.web.DataSet.extend({
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
        this.offset = 0;
        this._length;
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
     * @returns {$.Deferred}
     */
    read_slice: function (fields, options) {
        options = options || {};
        var self = this;
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
            self._length = result.length;
            return result.records;
        });
    },
    get_domain: function (other_domain) {
        if (other_domain) {
            return new openerp.web.CompoundDomain(this.domain, other_domain);
        }
        return this.domain;
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
    },
    size: function () {
        if (this._length !== undefined) {
            return this._length;
        }
        return this._super();
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
    default_get: function(fields, options) {
        return this._super(fields, options).then(this.on_default_get);
    },
    on_default_get: function(res) {
        this.last_default_get = res;
    },
    create: function(data, callback, error_callback) {
        var cached = {id:_.uniqueId(this.virtual_id_prefix), values: data,
            defaults: this.last_default_get};
        this.to_create.push(_.extend(_.clone(cached), {values: _.clone(cached.values)}));
        this.cache.push(cached);
        var prom = $.Deferred().then(callback);
        prom.resolve({result: cached.id});
        return prom.promise();
    },
    write: function (id, data, options, callback) {
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
            this.on_change();
        var to_return = $.Deferred().then(callback);
        to_return.resolve({result: true});
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
        return $.async_when({result: true}).then(callback);
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
            var rpc_promise = this._super(to_get, fields, options).then(function(records) {
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
    evict_from_cache: function (id) {
        for (var i = 0, len = this.cache.length; i < len; ++i) {
            var record = this.cache[i];
            // if record we call the button upon is in the cache
            if (record.id === id) {
                // evict it so it gets reloaded from server
                this.cache.splice(i, 1);
                break;
            }
        }
    },
    call_button: function (method, args, callback, error_callback) {
        this.evict_from_cache(args[0][0]);
        return this._super(method, args, callback, error_callback);
    },
    alter_ids: function(n_ids) {
    	this._super(n_ids);
        this.on_change();
    },
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
    default_get: function(fields, options) {
        return this._super(fields, options).then(this.on_default_get);
    },
    on_default_get: function(result) {},
    create: function(data, callback, error_callback) {
        this.on_create(data);
        if (this.create_function) {
            return this.create_function(data, callback, error_callback);
        } else {
            console.warn("trying to create a record using default proxy dataset behavior");
            return $.async_when({"result": undefined}).then(callback);
        }
    },
    on_create: function(data) {},
    write: function (id, data, options, callback) {
        options = options || {};
        this.on_write(id, data, options);
        if (this.write_function) {
            return this.write_function(id, data, options, callback);
        } else {
            console.warn("trying to write a record using default proxy dataset behavior");
            return $.async_when({"result": true}).then(callback);
        }
    },
    on_write: function(id, data) {},
    unlink: function(ids, callback, error_callback) {
        this.on_unlink(ids);
        console.warn("trying to unlink a record using default proxy dataset behavior");
        return $.async_when({"result": true}).then(callback);
    },
    on_unlink: function(ids) {}
});

openerp.web.Model = openerp.web.CallbackEnabled.extend({
    init: function(model_name) {
        this._super();
        this.model_name = model_name;
    },
    rpc: function() {
        var c = openerp.connection;
        return c.rpc.apply(c, arguments);
    },
    /*
     * deprecated because it does not allow to specify kwargs, directly use call() instead
     */
    get_func: function(method_name) {
        var self = this;
        return function() {
            return self.call(method_name, _.toArray(arguments), {});
        };
    },
    call: function (method, args, kwargs) {
        return this.rpc('/web/dataset/call_kw', {
            model: this.model_name,
            method: method,
            args: args,
            kwargs: kwargs
        });
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
