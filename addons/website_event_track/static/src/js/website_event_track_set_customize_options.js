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

    _initCheckbox: function () {
        this._rpc({
            model: this.modelName,
            method: 'read',
            args: [[this.eventId], ['website_menu', 'website_url', 'website_track', 'website_track_proposal']],
        }).then((data) => {
            if (data[0]['website_track']) {
                this.$displayTalksInput.attr('checked', 'checked');
            }
            if (data[0]['website_track_proposal']) {
                this.$allowTalksInput.attr('checked', 'checked');
            }
            if (data[0]['website_menu']) {
                this.$submenuInput.attr('checked', 'checked');
            } else {
                this.$displayTalksInput.closest('a').addClass('d-none');
                this.$allowTalksInput.closest('a').addClass('d-none');
            }
            this.eventUrl = data[0]['website_url'];
        });
    },

    _onAllowTalkProposalChange: function () {
        var checkboxValue = this.$allowTalksInput.is(':checked');
        this._toggleTalkProposal(checkboxValue);
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

    _onDisplayTalksChange: function () {
        var checkboxValue = this.$displayTalksInput.is(':checked');
        this._toggleDisplayTalks(checkboxValue);
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
