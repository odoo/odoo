odoo.define('website.set_view_track', function (require) {
"use strict";

var CustomizeMenu = require('website.customizeMenu');
var Widget = require('web.Widget');

var TrackPage = Widget.extend({
    template: 'website.track_page',
    xmlDependencies: ['/website/static/src/xml/track_page.xml'],
    events: {
        'change #switch-track-page': '_onTrackChange',
    },

    /**
     * @override
     */
    start: function () {
        this.$input = this.$('#switch-track-page');
        this._isTracked().then((data) => {
            if (data[0]['track']) {
                this.track = true;
                this.$input.attr('checked', 'checked');
            } else {
                this.track = false;
            }
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _isTracked: function (val) {
        var viewid = $('html').data('viewid');
        if (!viewid) {
            return Promise.reject();
        } else {
            return this._rpc({
                model: 'ir.ui.view',
                method: 'read',
                args: [[viewid], ['track']],
            });
        }
    },
    /**
     * @private
     */
    _onTrackChange: function (ev) {
        var checkboxValue = this.$input.is(':checked');
        if (checkboxValue !== this.track) {
            this.track = checkboxValue;
            this._trackPage(checkboxValue);
        }
    },
    /**
     * @private
     */
    _trackPage: function (val) {
        var viewid = $('html').data('viewid');
        if (!viewid) {
            return Promise.reject();
        } else {
            return this._rpc({
                model: 'ir.ui.view',
                method: 'write',
                args: [[viewid], {track: val}],
            });
        }
    },
});

CustomizeMenu.include({
    _loadCustomizeOptions: function () {
        var self = this;
        var def = this._super.apply(this, arguments);
        return def.then(function () {
            if (!self.__trackpageLoaded) {
                self.__trackpageLoaded = true;
                self.trackPage = new TrackPage(self);
                self.trackPage.appendTo(self.$el.children('.dropdown-menu'));
            }
        });
    },
});

});
