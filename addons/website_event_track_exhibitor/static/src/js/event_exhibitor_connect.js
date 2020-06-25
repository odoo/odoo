odoo.define('website_event_track_exhibitor.event_exhibitor_connect', function (require) {
'use strict';

var core = require('web.core');
var Dialog = require('web.Dialog');
var publicWidget = require('web.public.widget');

var QWeb = core.qweb;
var _t = core._t;

var ExhibitorConnectClosedDialog = Dialog.extend({
    events: _.extend({}, Dialog.prototype.events, {
        'click .o_wesponsor_js_connect_modal_contry': '_onClickCountryFlag',
    }),
    template: 'exhibitor.connect.closed.modal',

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
        this.sponsorId = options.sponsorId;
        this._super(parent, options);
    },

    /**
     * @override
     * Wait for fetching sponsor data;
     */
    willStart: function () {
        return Promise.all([
            this._super(...arguments),
            this._fetchSponsor()
        ]);
    },

    //---------------------------------------------------------------------
    // Private
    //---------------------------------------------------------------------

    /**
     * @private
     * @returns {Promise<*>} promise after fetching sponsor data, given its
     *   sponsorId. Necessary to render template content;
     */
    _fetchSponsor: function () {
        let self = this;
        let rpcPremise = this._rpc({
            model: 'event.sponsor',
            method: 'read',
            args: [
                this.sponsorId,
                ['name', 'subtitle', 'sponsor_type_id',
                 'website', 'email', 'phone',
                 'website_description', 'website_image_url',
                 'hour_from', 'hour_to', 'is_in_opening_hours',
                 'country_id', 'country_flag_url',
                ],
            ],
        }).then(function (readData) {
            self.sponsorData = readData[0];
            if (self.sponsorData.country_id) {
                self.sponsorData.country_name = self.sponsorData.country_id[1];
                self.sponsorData.country_id = self.sponsorData.country_id[0];
            }
            else {
                self.sponsorData.country_name = false;
            }
            if (self.sponsorData.sponsor_type_id) {
                self.sponsorData.sponsor_type_name = self.sponsorData.sponsor_type_id[1];
                self.sponsorData.sponsor_type_id = self.sponsorData.sponsor_type_id[0];
            }
            else {
                self.sponsorData.sponsor_type_name = false;
            }
            return Promise.resolve();
        });
        return rpcPremise;
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
        this._super(...arguments);
        this._onConnectClick = _.debounce(this._onConnectClick, 500, true);
    },

    /**
     * @override
     * @public
     */
    start: function () {
        this._super(...arguments);
        this.eventIsOngoing = this.$el.data('eventIsOngoing') || false;
        this.sponsorIsOngoing = this.$el.data('sponsorIsOngoing') || false;
    },

    //--------------------------------------------------------------------------
    // Handlers
    //-------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     * On click, if sponsor is not within opening hours, display a modal instead
     * of redirecting on the sponsor view;
     */
    _onConnectClick: function (ev) {
        if (this.eventIsOngoing && ! this.sponsorIsOngoing) {
            ev.stopPropagation();
            ev.preventDefault();
            return this._openClosedDialog();
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _openClosedDialog: function ($element) {
        const sponsorId = this.$el.data('sponsorId');
        return new ExhibitorConnectClosedDialog(
            this, {
                sponsorId: sponsorId,
            }
        ).open();
    },

});


return {
    ExhibitorConnectClosedDialog: ExhibitorConnectClosedDialog,
    eventExhibitorConnect: publicWidget.registry.eventExhibitorConnect,
};

});
