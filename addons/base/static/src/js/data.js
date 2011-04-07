
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
    create: function() {
    },
    write: function (id, data, callback) {
        return this.rpc('/base/dataset/save', {
            model: this.model,
            id: id,
            data: data,
            context: this.context
        }, callback);
    },
    unlink: function() {
        this.notification['default']("Unlink", ids);
    },
    call: function (method, ids, args, callback) {
        ids = ids || [];
        args = args || [];
        return this.rpc('/base/dataset/call', {
            model: this.model,
            method: method,
            ids: ids,
            args: args
        }, callback);
    },
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
    },
});

openerp.base.DataSetSearch =  openerp.base.DataSet.extend({
    init: function(session, model) {
        this._super(session, model);
        this.domain = [];
        this.sort = [];
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
            sort: this.sort,
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
});

openerp.base.DataSetRelational =  openerp.base.DataSet.extend( /** @lends openerp.base.DataSet# */{
});

};

// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
