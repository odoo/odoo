
openerp.base.data = function(openerp) {

openerp.base.DataGroup =  openerp.base.Controller.extend(
    /** @lends openerp.base.DataGroup# */{
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

openerp.base.DataSet =  openerp.base.Controller.extend(
    /** @lends openerp.base.DataSet# */{
    /**
     * Management interface between views and the collection of selected
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

        this._ids = [];
        this._active_ids = null;
        this._active_id_index = 0;

        this._sort = [];
        this._domain = [];
        this._context = {};
    },
    start: function() {
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
    fetch: function (fields, offset, limit) {
        offset = offset || 0;
        this.rpc('/base/dataset/find', {
            model: this.model,
            fields: fields,
            domain: this._domain,
            context: this._context,
            sort: this._sort,
            offset: offset,
            limit: limit
        }, _.bind(function (records) {
            var data_records = _.map(
                records, function (record) {
                    return new openerp.base.DataRecord(this.session, this.model, fields, record);
                }, this);

            this.on_fetch(data_records, {
                offset: offset,
                limit: limit,
                domain: this._domain,
                context: this._context,
                sort: this._sort
            });
        }, this));
        return this;
    },
    /**
     * Fires after the DataSet fetched the records matching its internal ids selection
     *
     * TODO: remove?
     *
     * @event
     * @param {Array} records An array of the DataRecord fetched
     * @param event The on_fetch event object
     * @param {Number} event.offset the offset with which the original DataSet#fetch call was performed
     * @param {Number} event.limit the limit set on the original DataSet#fetch call
     * @param {Array} event.domain the domain set on the DataSet before DataSet#fetch was called
     * @param {Object} event.context the context set on the DataSet before DataSet#fetch was called
     * @param {Array} event.sort the sorting criteria used to get the ids
     */
    on_fetch: function (records, event) { 
    },

    /**
     * Fetch all the currently active records for this DataSet (records selected via DataSet#select)
     *
     * TODO: add fields, return deferred
     *
     * @returns itself
     */
    active_ids: function (fields) {
        this.rpc('/base/dataset/get', {
            ids: this.get_active_ids(),
            model: this.model
        }, _.bind(function (records) {
            this.on_active_ids(_.map(
                records, function (record) {
                    return new openerp.base.DataRecord(this.session, this.model, fields, record);
                }, this));
        }, this));
        return this;
    },

    /**
     * Fires after the DataSet fetched the records matching its internal active ids selection
     *
     * TODO: remove?
     *
     * @event
     * @param {Array} records An array of the DataRecord fetched
     */
    on_active_ids: function (records) { 
    },

    /**
     * Fetches the current active record for this DataSet
     *
     * TODO: add field, return deferred?
     *
     * @returns itself
     */
    active_id: function (fields) {
        this.rpc('/base/dataset/get', {
            ids: [this.get_active_id()],
            model: this.model
        }, _.bind(function (records) {
            var record = records[0];
            this.on_active_id(
                record && new openerp.base.DataRecord(
                        this.session, this.model,
                        fields, record));
        }, this));
        return this;
    },

    /**
     * Fires after the DataSet fetched the record matching the current active record
     *
     * @event
     * @param record the record matching the provided id, or null if there is no record for this id
     */
    on_active_id: function (record) {

    },

    /**
     * Configures the DataSet
     *
     * @param options DataSet options
     * @param {Array} options.domain the domain to assign to this DataSet for filtering
     * @param {Object} options.context the context this DataSet should use during its calls
     * @param {Array} options.sort the sorting criteria for this DataSet
     * @returns itself
     */
    set: function (options) {
        if (options.domain) {
            this._domain = _.clone(options.domain);
        }
        if (options.context) {
            this._context = _.clone(options.context);
        }
        if (options.sort) {
            this._sort = _.clone(options.sort);
        }
        return this;
    },

    /**
     * Activates the previous id in the active sequence. If there is no previous id, wraps around to the last one
     * @returns itself
     */
    prev: function () {
        this._active_id_index -= 1;
        if (this._active_id_index < 0) {
            this._active_id_index = this._active_ids.length - 1;
        }
        return this;
    },

    /**
     * Activates the next id in the active sequence. If there is no next id, wraps around to the first one
     * @returns itself
     */
    next: function () {
        this._active_id_index += 1;
        if (this._active_id_index >= this._active_ids.length) {
            this._active_id_index = 0;
        }
        return this;
    },

    /**
     * Sets active_ids by value:
     *
     * * Activates all ids part of the current selection
     *
     * * Sets active_id to be the first id of the selection
     *
     * @param {Array} ids the list of ids to activate
     * @returns itself
     */
    select: function (ids) {
        this._active_ids = ids;
        this._active_id_index = 0;
        return this;
    },

    /**
     * Fetches the ids of the currently selected records, if any.
     */
    get_active_ids: function () {
        return this._active_ids;
    },

    /**
     * Sets the current active_id by value
     *
     * If there are no active_ids selected, selects the provided id as the sole active_id
     *
     * If there are ids selected and the provided id is not in them, raise an error
     *
     * @param {Object} id the id to activate
     * @returns itself
     */
    activate: function (id) {
        if(!this._active_ids) {
            this._active_ids = [id];
            this._active_id_index = 0;
        } else {
            var index = _.indexOf(this._active_ids, id);
            if (index == -1) {
                throw new Error(
                    "Could not find id " + id +
                    " in array [" + this._active_ids.join(', ') + "]");
            }
            this._active_id_index = index;
        }
        return this;
    },

    /**
     * Fetches the id of the current active record, if any.
     *
     * @returns record? record id or <code>null</code>
     */
    get_active_id: function () {
        if (!this._active_ids) {
            return null;
        }
        return this._active_ids[this._active_id_index];
    }
});

openerp.base.DataRecord =  openerp.base.Controller.extend({
    init: function(session, model, fields, values) {
        this._super(session, null);
        this.model = model;
        this.id = values.id || null;
        this.fields = fields;
        this.values = values;
    },
    on_change: function() {
    },
    on_reload: function() {
    }
});

};

// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
