odoo.define('lunch.LunchKanbanModel', function (require) {
"use strict";

/**
 * This file defines the Model for the Lunch Kanban view, which is an
 * override of the KanbanModel.
 */

var KanbanModel = require('web.KanbanModel');

var LunchKanbanModel = KanbanModel.extend({
    init: function () {
        this.locationId = false;
        this.userId = false;

        this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {integer|false}
     */
    getCurrentLocationId: function () {
        return this.locationId;
    },
    load: function () {
        var self = this;
        var args = arguments;
        var _super = this._super;

        return this._initUserLocation().then(function (locationId) {
            var params = args[0];
            self._addOrUpdate(params.domain, self._buildLocationDomainLeaf());

            return _super.apply(self, args);
        });
    },
    reload: function (id, options) {
        var domain = options && options.domain || this.localData[id].domain;

        this._addOrUpdate(domain, this._buildLocationDomainLeaf());
        options = _.extend(options, {domain: domain});

        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

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
    /**
     * Builds the domain leaf corresponding to the current user's location
     *
     * @return {Array}
     */
    _buildLocationDomainLeaf: function() {
        var locationId = this.getCurrentLocationId();
        if (locationId) {
            return ['is_available_at', 'in', [locationId]];
        }
    },
    /**
     * Since this widget may add stuff in the domain (the location of the user)
     * this method allows to build the domain before actually loading the whole model
     * to inject at search panel's creation from the View
     *
     * @return {Deferred} resolved with a domain
     */
    _getAdditionalSearchPanelDomain: function () {
        var self = this;
        return this._initUserLocation().then(function () {
            return [self._buildLocationDomainLeaf()];
        });
    },
    _getUserLocation: function () {
        return this._rpc({
            route: '/lunch/user_location_get',
            params: {
                user_id: this.userId,
            },
        });
    },
    /**
     * Gets the user location once.
     * Can be triggered from anywhere
     * Useful to inject the location domain in the search panel
     *
     * @return {Deferred}
     */
    _initUserLocation: function () {
        var self = this;
        if (!this._defInitLocation) {
            this._defInitLocation = new $.Deferred();
            this._getUserLocation().then(function (locationId) {
                self.locationId = locationId;
                self._defInitLocation.resolve();
            });
        }
        return this._defInitLocation;
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
