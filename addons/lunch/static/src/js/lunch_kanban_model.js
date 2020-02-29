odoo.define('lunch.LunchKanbanModel', function (require) {
"use strict";

/**
 * This file defines the Model for the Lunch Kanban view, which is an
 * override of the KanbanModel.
 */

var session = require('web.session');
var KanbanModel = require('web.KanbanModel');

var LunchKanbanModel = KanbanModel.extend({
    init: function () {
        this.locationId = false;
        this.userId = false;
        this._promInitLocation = null;

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
    /**
     * @return {Promise} resolved with the location domain
     */
    getLocationDomain: function () {
        var self = this;
        return this._initUserLocation().then(function () {
            return self._buildLocationDomainLeaf() ? [self._buildLocationDomainLeaf()]: [];
        });
    },
    load: function () {
        var self = this;
        var args = arguments;
        var _super = this._super;

        return this._initUserLocation().then(function () {
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
        if (subDomain && subDomain.length) {
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
        }

        return domain;
    },
    /**
     * Builds the domain leaf corresponding to the current user's location
     *
     * @private
     * @return {Array}
     */
    _buildLocationDomainLeaf: function () {
        var locationId = this.getCurrentLocationId();
        if (locationId) {
            return ['is_available_at', 'in', [locationId]];
        }
    },
    _getUserLocation: function () {
        return this._rpc({
            route: '/lunch/user_location_get',
            params: {
                context: session.user_context,
                user_id: this.userId,
            },
        });
    },
    /**
     * Gets the user location once.
     * Can be triggered from anywhere
     * Useful to inject the location domain in the search panel
     *
     * @private
     * @return {Promise}
     */
    _initUserLocation: function () {
        var self = this;
        if (!this._promInitLocation) {
            this._promInitLocation = new Promise(function (resolve) {
                self._getUserLocation().then(function (locationId) {
                    self.locationId = locationId;
                    resolve();
                });
            });
        }
        return this._promInitLocation;
    },
    _updateLocation: function (locationId) {
        this.locationId = locationId;
        return Promise.resolve();
    },
    _updateUser: function (userId) {
        this.userId = userId;
        this._promInitLocation = null;
        return this._initUserLocation();
    }
});

return LunchKanbanModel;

});
