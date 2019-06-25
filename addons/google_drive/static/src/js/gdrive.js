odoo.define('google_drive.sidebar', function (require) {
"use strict";

/**
 * The purpose of this file is to include the Sidebar widget to add Google
 * Drive related items.
 */

var Sidebar = require('web.Sidebar');


Sidebar.include({
    // TO DO: clean me in master
    /**
     * @override
     */
    start: function () {
        var def;
        if (this.options.viewType === "form") {
            def = this._addGoogleDocItems(this.env.model, this.env.activeIds[0]);
        }
        return Promise.resolve(def).then(this._super.bind(this));
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {string} model
     * @param {integer} resID
     * @returns {Promise}
     */
    _addGoogleDocItems: function (model, resID) {
        var self = this;
        if (!resID) {
            return Promise.resolve();
        }
        var gdoc_item = _.indexOf(_.pluck(self.items.other, 'classname'), 'oe_share_gdoc');
        if (gdoc_item !== -1) {
            self.items.other.splice(gdoc_item, 1);
        }
        return this._rpc({
            args: [this.env.model, resID],
            context: this.env.context,
            method: 'get_google_drive_config',
            model: 'google.drive.config',
        }).then(function (r) {
            if (!_.isEmpty(r)) {
                _.each(r, function (res) {
                    var already_there = false;
                    for (var i = 0; i < self.items.other.length; i++) {
                        var item = self.items.other[i];
                        if (item.classname === 'oe_share_gdoc' && item.label.indexOf(res.name) > -1) {
                            already_there = true;
                            break;
                        }
                    }
                    if (!already_there) {
                        self._addItems('other', [{
                            callback: self._onGoogleDocItemClicked.bind(self, res.id),
                            classname: 'oe_share_gdoc',
                            config_id: res.id,
                            label: res.name,
                            res_id: resID,
                            res_model: model,
                        }]);
                    }
                });
            }
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {integer} configID
     * @param {integer} resID
     */
    _onGoogleDocItemClicked: function (configID) {
        var self = this;
        var resID = this.env.activeIds[0];
        var domain = [['id', '=', configID]];
        var fields = ['google_drive_resource_id', 'google_drive_client_id'];
        this._rpc({
            args: [domain, fields],
            method: 'search_read',
            model: 'google.drive.config',
        }).then(function (configs) {
            self._rpc({
                args: [configID, resID, configs[0].google_drive_resource_id],
                context: self.env.context,
                method: 'get_google_drive_url',
                model: 'google.drive.config',
            }).then(function (url) {
                if (url){
                    window.open(url, '_blank');
                }
            });
        });
    },

});

return Sidebar;
});
