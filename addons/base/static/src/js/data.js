
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

        this.ids = [];
        this.offset
        this.index = 0;
        this.count = 0;

        this.sort = [];
        this.domain = [];
        this.context = {};
    },
    start: function() {
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

    default_get: function() {
    },
    create: function() {
    },
    /**
     * Fetch all the records selected by this DataSet, based on its domain
     * and context.
     *
     * Fires the on_ids event.
     *
     * TODO: return deferred
     *
     * @param {Number} [offset=0] The index from which selected records should be returned
     * @param {Number} [limit=null] The maximum number of records to return
     * @returns itself
     */
    // Rename into read() ?
    fetch: function (fields, offset, limit, callback) {
        var self = this;
        offset = offset || 0;
        this.rpc('/base/dataset/find', {
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
    fetch_ids: function (ids, fields, callback) {
        var self = this;
        this.rpc('/base/dataset/get', {
            model: this.model,
            ids: ids,
            fields: fields
        }, callback);
    },
    fetch_index: function (fields, callback) {
        if (_.isEmpty(this.ids)) {
            callback([]);
        } else {
            fields = fields || false;
            this.fetch_ids([this.ids[this.index]], fields, function(records) {
                callback(records[0]);
            });
        }
    },
    write: function (id, data, callback) {
        this.rpc('/base/datarecord/save', {
            model: this.model,
            id: id,
            data: data,
            context: this.context
        }, callback);
    },
    unlink: function() {
    }
});

openerp.base.DataSetSearch =  openerp.base.DataSet.extend( /** @lends openerp.base.DataSet# */{
});

openerp.base.DataSetRelational =  openerp.base.DataSet.extend( /** @lends openerp.base.DataSet# */{
});

};

// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
