odoo.define('website_event_track.our_sponsors', function (require) {

const { qweb } = require('web.core');
const publicWidget = require('web.public.widget');

publicWidget.registry.eventSponsors = publicWidget.Widget.extend({
    selector: '.o_our_sponsors',
    xmlDependencies: ['/website_event_track/static/src/xml/our_sponsors.xml'],

    /**
     * @override
     */
    async start() {
        await this._super.apply(this, arguments);
        const data = await this._rpc({
            route: '/event/' + this.$target.data('eventId') + '/our_sponsors',
        });
        this.$target.find('#sponsor_details').html(
            $(qweb.render('website_event_track.ourSponsors', {
                sponsor_ids: data
            }))
        );
    },
});
});
