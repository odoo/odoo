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
        this.uniqueId = _.uniqueId('o_event_our_sponsors_');
    },
    /**
     * @override
     */
    start: async function () {
        await this._super.apply(this, arguments);
        const self = this;
        const sponsors = this.$el.attr('data-sponsors');
        this.sponsors = sponsors ? sponsors.split(',') : [];

        if (this.sponsors) {
            await this._rpc({
            route: '/event/our_sponsors',
            params: {
                'sponsor_ids': this.sponsors
                }
            }).then((res) => {
                self._render(res);
            })
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Renders sponsors for the event
     *
     * @private
     */
    _render: function (sponsors) {
        this.sponsorsTemplate = $(qweb.render('website_event_track.ourSponsors', {
            uniqueId: this.uniqueId,
            sponsors: sponsors,
        }));
        this.$('.o_our_sponsors').html(this.sponsorsTemplate).css('display', '');     
    }
});
});
