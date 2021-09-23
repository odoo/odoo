/** @odoo-module **/

import {ChannelCreateDialog} from '@website_slides/js/website_slides.editor';

ChannelCreateDialog.include({
    xmlDependencies: ChannelCreateDialog.prototype.xmlDependencies.concat(
        ['/website_sale_slides/static/src/xml/website_slides_channel.xml']
    ),

    events: _.extend({}, ChannelCreateDialog.prototype.events, {
        'change input[name="enroll"]': '_onEnrollChanged',
    }),

    willStart: async function () {
        await this._super();

        this.products = await this._rpc({route: '/slides/get_course_products'});
    },

    /**
     * @private
     */
    _onEnrollChanged: function (ev) {
        this.$('.o_wslides_course_products').toggleClass('d-none', ev.target.value !== 'payment');
    },
});
