odoo.define('website_event_track_exhibitor.event_exhibitor_connect', function (require) {
'use strict';

var core = require('web.core');
var Dialog = require('web.Dialog');
var publicWidget = require('web.public.widget');

var QWeb = core.qweb;
var _t = core._t;

var ExhibitorConnectClosedDialog = Dialog.extend({
    template: 'exhibitor.connect.closed.modal',
    events: _.extend({}, Dialog.prototype.events, {
        'click .o_wesponsor_js_connect_modal_contry': '_onClickCountryFlag',
    }),

    /**
     * @override
     * @param {Object} parent;
     * @param {Object} options holding a sponsorData obj with required values to
     *   display (see .xml for details);
     */
    init: function (parent, options) {
        options = _.defaults(options || {}, {
            size: 'medium',
            renderHeader: false,
            renderFooter: false,
        });
        this.sponsorData = options.sponsorData;
        console.log(this.sponsorData);
        this._super(parent, options);
    },
});


publicWidget.registry.eventExhibitorConnect = publicWidget.Widget.extend({
    events: {
        'click a': '_onConnectClick',
    },
    selector: '.o_wesponsor_js_connect',
    xmlDependencies: ['/website_event_track_exhibitor/static/src/xml/event_exhibitor_connect.xml'],

    /**
     * @override
     * @public
     */
    init: function () {
        this._super.apply(this, arguments);
        this._onConnectClick = _.debounce(this._onConnectClick, 500, true);
    },

    /**
     * @override
     * @public
     */
    start: function () {
        this._super.apply(this, arguments);
        this.isInOpeningHours = this.$el.data('isInOpeningHours') || false;
    },

    //--------------------------------------------------------------------------
    // Handlers
    //-------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onConnectClick: function (ev) {
        if (! this.isInOpeningHours) {
            ev.stopPropagation();
            ev.preventDefault();
            return this._openClosedDialog();
        }
        else {
            // ev.stopPropagation();
            // ev.preventDefault();
            // return this._openClosedDialog();
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _openClosedDialog: function ($element) {
        const sponsorData = this.$el.data();
        return new ExhibitorConnectClosedDialog(
            this, {
                sponsorData: sponsorData,
            }
        ).open();
    },

});


return {
    ExhibitorConnectClosedDialog: ExhibitorConnectClosedDialog,
    eventExhibitorConnect: publicWidget.registry.eventExhibitorConnect,
};

});
