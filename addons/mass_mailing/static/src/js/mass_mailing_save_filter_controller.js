odoo.define('mass_mailing.AddFavorite_controller', function(require) {
'use strict';

var FormView = require('web.FormView');
var FormController = require('web.FormController');
var viewRegistry = require('web.view_registry');


var MassMailingController = FormController.extend({
    custom_events: _.extend({}, FormController.prototype.custom_events, {
        'mass_mailing_save': '_createFilter',
        'mass_mailing_remove': '_removeFilter'
    }),
    /**
     * @private
     * @param {OdooEvent} ev
     */
    _createFilter: function (ev) {
        var self = this;
        var record = this.model.get(this.handle);
        this._rpc({
            model: 'mailing.saved.filters',
            method: 'create',
            args: [{
                name: ev.data.filterName,
                mailing_domain: record.data.mailing_domain
            }]
        }).then(function (result) {
            self.trigger_up('field_changed', {
                dataPointID: record.id,
                changes: {
                    filter_id: {id: result}
                },
            });
        });
    },

    /**
     * @private
     * @param {OdooEvent} ev
     */
    _removeFilter: function (ev) {
        var self = this;
        var record = this.model.get(this.handle);
        this._rpc({
            'model': 'mailing.saved.filters',
            'method': 'unlink',
            'args': [record.data.filter_id.data.id]
        }).then(function () {
            self.trigger_up('field_changed', {
                dataPointID: record.id,
                changes: {
                    filter_id: {
                        operation: 'DELETE',
                        ids: [record.data.filter_id.data.id]
                    }
                },
            });
        });
    }
});

var MassMailingFormView = FormView.extend({
    config: _.extend({}, FormView.prototype.config, {
        Controller: MassMailingController,
    }),
});

viewRegistry.add('mass_mailing_form', MassMailingFormView);

return MassMailingFormView;
});
