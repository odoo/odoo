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
    viewType: undefined,
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

        this.rendererParams.viewType = this.viewType;

        this.controllerParams.confirmOnDelete = true;
        this.controllerParams.archiveEnabled = 'active' in viewInfo.fields;
        this.controllerParams.hasButtons =
                'action_buttons' in params ? params.action_buttons : true;

        this.loadParams.fieldsInfo = viewInfo.fieldsInfo;
        this.loadParams.fields = viewInfo.fields;
        this.loadParams.context = params.context || {};
        this.loadParams.limit = parseInt(viewInfo.arch.attrs.limit, 10) || params.limit;
        this.loadParams.viewType = this.viewType;
        this.loadParams.parentID = params.parentID;
        this.recordID = params.recordID;

        this.model = params.model;
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
            var self = this;
            var record = this.model.get(this.recordID);
            var viewType = this.viewType;
            var viewFields = Object.keys(record.fieldsInfo[viewType]);
            var fieldNames = _.difference(viewFields, Object.keys(record.data));
            var fieldsInfo = record.fieldsInfo[viewType];

            // Suppose that in a form view, there is an x2many list view with
            // a field F, and that F is also displayed in the x2many form view.
            // In this case, F is represented in record.data (as it is known by
            // the x2many list view), but the loaded information may not suffice
            // in the form view (e.g. if field is a many2many list in the form
            // view, or if it is displayed by a widget requiring specialData).
            // So when this happens, F is added to the list of fieldNames to fetch.
            _.each(viewFields, function (name) {
                if (!_.contains(fieldNames, name)) {
                    var fieldType = record.fields[name].type;
                    var fieldInfo = fieldsInfo[name];

                    // SpecialData case: field requires specialData that haven't
                    // been fetched yet.
                    if (fieldInfo.Widget) {
                        var requiresSpecialData = fieldInfo.Widget.prototype.specialData;
                        if (requiresSpecialData && !(name in record.specialData)) {
                            fieldNames.push(name);
                            return;
                        }
                    }

                    // X2Many case: field is an x2many displayed as a list or
                    // kanban view, but the related fields haven't been loaded yet.
                    if ((fieldType === 'one2many' || fieldType === 'many2many')) {
                        if (!('fieldsInfo' in record.data[name])) {
                            fieldNames.push(name);
                        } else {
                            var fieldViews = fieldInfo.views || fieldInfo.fieldsInfo || {};
                            var fieldViewTypes = Object.keys(fieldViews);
                            var recordViewTypes = Object.keys(record.data[name].fieldsInfo);
                            if (_.difference(fieldViewTypes, recordViewTypes).length) {
                                fieldNames.push(name);
                            }
                        }
                    }
                }
            });

            var def;
            if (fieldNames.length) {
                // Some fields in the new view weren't in the previous one, so
                // we might have stored changes for them (e.g. coming from
                // onchange RPCs), that we haven't been able to process earlier
                // (because those fields were unknow at that time). So we ask
                // the model to process them.
                def = this.model.applyRawChanges(record.id, viewType).then(function () {
                    if (!self.model.isNew(record.id)) {
                        return self.model.reload(record.id, {
                            fieldNames: fieldNames,
                            keepChanges: true,
                            viewType: viewType,
                        });
                    }
                });
            }
            return $.when(def).then(function () {
                return record.id;
            });
        }
        return this._super.apply(this, arguments);
    },
});

return BasicView;

});
