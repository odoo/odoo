
openerp.base.data = function(openerp) {

openerp.base.DataGroup =  openerp.base.Controller.extend( /** @lends openerp.base.DataGroup# */{
    /**
     * Management interface between views and the collection of selected OpenERP
     * records (represents the view's state?)
     *
     * @constructs
     * @extends openerp.base.Controller
     * @param {openerp.base.Session} session Current OpenERP session
     */
    init: function(session) {
        this._super(session, null);
    }
});

openerp.base.DataSet =  openerp.base.Controller.extend( /** @lends openerp.base.DataSet# */{
    /**
     * DateaManagement interface between views and the collection of selected
     * OpenERP records (represents the view's state?)
     *
     * @constructs
     * @extends openerp.base.Controller
     *
     * @param {openerp.base.Session} session current OpenERP session
     * @param {String} model the OpenERP model this dataset will manage
     */
    init: function(session, model) {
        this._super(session);
        this.model = model;
        this.context = {};
        this.index = 0;
        this.count = 0;
    },
    start: function() {
    },
    previous: function () {
        this.index -= 1;
        if (this.index < 0) {
            this.index = this.count - 1;
        }
        return this;
    },
    next: function () {
        this.index += 1;
        if (this.index >= this.count) {
            this.index = 0;
        }
        return this;
    },
    /**
     * Read records.
     */
    read_ids: function (ids, fields, callback) {
        var self = this;
        this.rpc('/base/dataset/get', {
            model: this.model,
            ids: ids,
            fields: fields
        }, callback);
    },
    /**
     * Read a slice of the records represented by this DataSet, based on its
     * domain and context.
     *
     * @param {Number} [offset=0] The index from which selected records should be returned
     * @param {Number} [limit=null] The maximum number of records to return
     */
    read_slice: function (fields, offset, limit, callback) {
    },
    /**
     * Read the indexed record.
     */
    read_index: function (fields, callback) {
        if (_.isEmpty(this.ids)) {
            callback([]);
        } else {
            fields = fields || false;
            this.read_ids([this.ids[this.index]], fields, function(records) {
                callback(records[0]);
            });
        }
    },
    default_get: function(fields, callback) {
        return this.rpc('/base/dataset/default_get', {
            model: this.model,
            fields: fields,
            context: this.context
        }, callback);
    },
    create: function(data, callback) {
        return this.rpc('/base/dataset/create', {
            model: this.model,
            data: data,
            context: this.context
        }, callback);
    },
    write: function (id, data, callback) {
        return this.rpc('/base/dataset/save', {
            model: this.model,
            id: id,
            data: data,
            context: this.context
        }, callback);
    },
    unlink: function(ids) {
        this.notification.notify("Unlink", ids);
    },
    call: function (method, ids, args, callback) {
        this.notification.notify(
            "Calling", this.model + '#' + method + '(' + ids + ')');
        ids = ids || [];
        args = args || [];
        return this.rpc('/base/dataset/call', {
            model: this.model,
            method: method,
            ids: ids,
            args: args
        }, callback);
    },
    exec_workflow: function (id, signal, callback) {
        return this.rpc('/base/dataset/exec_workflow', {
            model: this.model,
            id: id,
            signal: signal
        }, callback);
    }
});

openerp.base.DataSetStatic =  openerp.base.DataSet.extend({
    init: function(session, model) {
        this._super(session, model);
        // all local records
        this.ids = [];
        this.count = 0;
    },
    read_slice: function (fields, offset, limit, callback) {
        this.read_ids(this.ids.slice(offset, offset + limit));
    }
});

openerp.base.DataSetSearch =  openerp.base.DataSet.extend({
    init: function(session, model) {
        this._super(session, model);
        this.domain = [];
        this._sort = [];
        this.offset = 0;
        // subset records[offset:offset+limit]
        // is it necessary ?
        this.ids = [];
    },
    read_slice: function (fields, offset, limit, callback) {
        var self = this;
        offset = offset || 0;
        // cached search, not sure it's a good idea
        if(this.offset <= offset) {
            var start = offset - this.offset;
            if(this.ids.length - start >= limit) {
                // TODO: check if this could work do only read if possible
                // return read_ids(ids.slice(start,start+limit),fields,callback)
            }
        }
        this.rpc('/base/dataset/search_read', {
            model: this.model,
            fields: fields,
            domain: this.domain,
            context: this.context,
            sort: this.sort(),
            offset: offset,
            limit: limit
        }, function (records) {
            self.offset = offset;
            self.count = records.length;    // TODO: get real count
            for (var i=0; i < records.length; i++ ) {
                self.ids.push(records[i].id);
            }
            callback(records);
        });
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
            return _.map(this._sort, function (criteria) {
                if (criteria[0] === '-') {
                    return criteria.slice(1) + ' DESC';
                }
                return criteria + ' ASC';
            }).join(', ');
        }

        var reverse = force_reverse || (this._sort[0] === field);
        this._sort = _.without(this._sort, field, '-' + field);

        this._sort.unshift((reverse ? '-' : '') + field);
        return undefined;
    }
});

openerp.base.DataSetRelational =  openerp.base.DataSet.extend( /** @lends openerp.base.DataSet# */{
});

openerp.base.DataSetMany2Many = openerp.base.DataSetStatic.extend({
    /* should extend DataSetStatic instead, but list view still does not support it
     */

    unlink: function(ids) {
        // just do nothing
    },
});

};

// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
