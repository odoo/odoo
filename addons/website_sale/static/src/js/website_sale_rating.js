odoo.define('website_sale.rating', function (require) {
    "use strict";

    var core = require('web.core');
    var ajax = require('web.ajax');
    var rating = require('rating.rating');
    var website_mail_thread = require('website_mail.thread');

    var qweb = core.qweb;

    ajax.loadXML('/rating/static/src/xml/rating_common.xml', qweb);

    website_mail_thread.WebsiteMailThread.include({
        prepend_message: function(message_data){
            var $elem = this._super.call(this, message_data);
            if(message_data['rating_default_value']){
                var rating_star = new rating.RatingStarWidget(this, {
                    'rating_default_value': message_data['rating_default_value'],
                    'rating_disabled': message_data['rating_disabled'],
                });
                rating_star.appendTo($elem.find('h5'));
                this.$('.stars i').mouseout();
            }
        },
    });

});
