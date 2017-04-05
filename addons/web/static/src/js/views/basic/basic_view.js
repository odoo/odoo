odoo.define('web.BasicView', function (require) {
"use strict";

/**
 * The BasicView is an abstract class designed to share code between views that
 * want to use a basicModel.  As of now, it is the form view, the list view and
 * the kanban view.
 *
 * The main focus of this class is to process the arch and extract field
 * attributes, as well as some other useful informations.
 */

var AbstractView = require('web.AbstractView');
var BasicController = require('web.BasicController');
var BasicModel = require('web.BasicModel');

var BasicView = AbstractView.extend({
    config: _.extend({}, AbstractView.prototype.config, {
        Model: BasicModel,
        Controller: BasicController,
    }),
    /**
     * process the fields_view to find all fields appearing in the views.
     * list those fields' name in this.fields_name, which will be the list
     * of fields read when data is fetched.
     * this.fields is the list of all field's description (the result of
     * the fields_get), where the fields appearing in the fields_view are
     * augmented with their attrs and some flags if they require a
     * particular handling.
     *
     * @param {Object} viewInfo
     * @param {Object} params
     */
    init: function (viewInfo, params) {
        this._super.apply(this, arguments);

        this.controllerParams.confirmOnDelete = true;
        this.controllerParams.archiveEnabled = 'active' in viewInfo.fields;
        this.controllerParams.hasButtons =
                'action_buttons' in params ? params.action_buttons : true;

        this.loadParams.fieldsInfo = viewInfo.fieldsInfo;
        this.loadParams.fields = viewInfo.fields;
        this.loadParams.limit = parseInt(viewInfo.arch.attrs.limit, 10) || params.limit;
        this.loadParams.viewType = this.viewType;
        this.recordID = params.recordID;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * In some cases, we already have a preloaded record
     *
     * @override
     * @private
     * @returns {Deferred}
     */
    _loadData: function () {
        if (this.recordID) {
            var record = this.model.get(this.recordID);
            var viewType = this.viewType;
            var viewFields = Object.keys(record.fieldsInfo[viewType]);
            var fieldNames = _.difference(viewFields, Object.keys(record.data));
            if (fieldNames.length && !this.model.isNew(record.id)) {
                return this.model.reload(this.recordID, {
                    fieldNames: fieldNames,
                    keepChanges: true,
                    viewType: viewType,
                });
            } else {
                return $.when(this.recordID);
            }
        }
        return this._super.apply(this, arguments);
    },
});

return BasicView;

});
