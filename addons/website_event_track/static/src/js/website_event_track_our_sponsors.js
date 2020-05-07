odoo.define('website_event_track.our_sponsors', function (require) {

const concurrency = require('web.concurrency');
const qweb = require('web.core').qweb;
const publicWidget = require('web.public.widget');


publicWidget.registry.eventSponsors = publicWidget.Widget.extend({
    selector: '.s_wevent_track_our_sponsors',
    xmlDependencies: ['/website_event_track/static/src/xml/website_event_track_our_sponsors.xml'],
    disabledInEditableMode: false,

    /**
     * @constructor
     */
    init: function () {
        this._super.apply(this, arguments);
        this._dp = new concurrency.DropPrevious();
        this.uniqueId = _.uniqueId('o_event_our_sponsors_');
    },
    /**
     * @override
     */
    start: function () {
        this._dp.add(this._fetch()).then(this._render.bind(this));
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Fetch sponsors for an event and returns sponsors or demo data.
     *
     * @private
     */
    _fetch: function () {
        return this._rpc({
            route: '/event/our_sponsors',
            params: {'res_id': this.$el.data('res-id')}
        }).then(sponsors => {
            // return demo data for snippet (in case of drag-drop sponsors snippet in edit mode)
            if (!(sponsors && sponsors.length)) {
                return [{
                        id: 0,
                        url: '#',
                        partner_name: 'Sponsor 1',
                        sponsor_type_id: {'name': 'Gold'}
                    }, {
                        id: 0,
                        url: '#',
                        partner_name: 'Sponsor 2',
                        sponsor_type_id: {'name': 'Silver'}
                    }, {
                        id: 0,
                        url: '#',
                        partner_name: 'Sponsor 3',
                        sponsor_type_id: {'name': 'Bronze'}
                    }]
            }
            return sponsors;
        });
    },

    /**
     * Renders sponsors for the event
     *
     * @private
     */
    _render: function (sponsors) {
        this.sponsorsList = $(qweb.render('website_event_track.ourSponsors', {
            uniqueId: this.uniqueId,
            sponsorsGroups: sponsors,
        }));
        this.$('.o_event_sponsors').html(this.sponsorsList).css('display', '');
        this.$el.toggleClass('d-none', !(sponsors && sponsors.length));
    }
});
});
