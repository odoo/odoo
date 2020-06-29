odoo.define('website_event_track.set_customize_options', function (require) {
"use strict";

var EventSpecificOptions = require('website_event.set_customize_options').EventSpecificOptions;

EventSpecificOptions.include({
    xmlDependencies: (EventSpecificOptions.prototype.xmlDependencies || [])
        .concat([
            '/website_event_track/static/src/xml/customize_options.xml',
        ]),

    events: _.extend({}, EventSpecificOptions.prototype.events, {
        'change #display-showcase-talks': '_onDisplayTalksChange',
        'change #allow-talk-proposal': '_onAllowTalkProposalChange',
    }),

    start: function () {
        this.$displayTalksInput = this.$('#display-showcase-talks');
        this.$allowTalksInput = this.$('#allow-talk-proposal');
        this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    _onAllowTalkProposalChange: function () {
        var checkboxValue = this.$allowTalksInput.is(':checked');
        this._toggleTalkProposal(checkboxValue);
    },

    _onDisplayTalksChange: function () {
        var checkboxValue = this.$displayTalksInput.is(':checked');
        this._toggleDisplayTalks(checkboxValue);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _getCheckboxFields: function () {
        var fields = this._super();
        fields = _.union(fields, ['website_track', 'website_track_proposal']);
        return fields;
    },

    _getCheckboxFieldMatch: function (checkboxField) {
        if (checkboxField === 'website_track') {
            return this.$displayTalksInput;
        }
        if (checkboxField === 'website_track_proposal') {
            return this.$allowTalksInput;
        }
        return this._super(checkboxField);
    },

    _initCheckboxCallback: function (rpcData) {
        this._super(rpcData);
        var submenuInput;
        if (rpcData[0]['website_track']) {
            submenuInput = this._getCheckboxFieldMatch('website_track');
            submenuInput.attr('checked', 'checked');
        }
        if (rpcData[0]['website_track_proposal']) {
            submenuInput = this._getCheckboxFieldMatch('website_track_proposal');
            submenuInput.attr('checked', 'checked');
        }
    },

    _toggleTalkProposal: function (val) {
        var self = this;
        this._rpc({
            model: this.modelName,
            method: 'toggle_website_track_proposal',
            args: [[this.eventId], val],
        }).then(function () {
            self._reloadEventPage();
        });
    },

    _toggleDisplayTalks: function (val) {
        var self = this;
        this._rpc({
            model: this.modelName,
            method: 'toggle_website_track',
            args: [[this.eventId], val],
        }).then(function () {
            self._reloadEventPage();
        });
    }

});

});
