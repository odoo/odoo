odoo.define('lunch.LunchKanbanModel', function (require) {
"use strict";

/**
 * This file defines the Model for the Lunch Kanban view, which is an
 * override of the KanbanModel.
 */

var KanbanModel = require('web.KanbanModel');
var core = require('web.core');

var _t = core._t;

var LunchKanbanModel = KanbanModel.extend({
    init: function () {
        this.locationId = false;
        this.userId = false;

        return this._super.apply(this, arguments);
    },
    load: function() {
        var self = this;
        var args = arguments;
        var _super = this._super;

        return this._getUserLocation().then(function (locationId) {
            var params = args[0];
            self.locationId = locationId;
            self._addOrUpdate(params.domain, ['is_available_at', 'in', [locationId]]);

            return _super.apply(self, args);
        });
    },
    reload: function (id, options) {
        var domain = options.domain || this.localData[id].domain;

        this._addOrUpdate(domain, ['is_available_at', 'in', [this.locationId]]);
        options = _.extend(options, {domain: domain});

        return this._super.apply(this, arguments);
    },

    _addOrUpdate: function (domain, subDomain) {
        var key = subDomain[0];
        var index = _.findIndex(domain, function (val) {
            return val[0] === key;
        });

        if (index < 0) {
            domain.push(subDomain);
        } else {
            domain[index] = subDomain;
        }

        return domain;
    },
    _getUserLocation: function () {
        return this._rpc({
            route: '/lunch/user_location_get',
            params: {
                user_id: this.userId,
            },
        });
    },
    _updateLocation: function (locationId) {
        this.locationId = locationId;
        return $.when();
    },
    _updateUser: function (userId) {
        var self = this;

        this.userId = userId;

        return this._getUserLocation().then(function (locationId) {
            self.locationId = locationId;
        });
    }
});

return LunchKanbanModel;

});
