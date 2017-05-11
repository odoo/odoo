odoo.define('web.rainbow_man', function (require) {
"use strict";

var ajax = require("web.ajax");
var Widget = require('web.Widget');
var core = require('web.core');
var qweb = core.qweb;

ajax.loadXML("/web/static/src/xml/rainbow_man.xml", qweb);

var RainbowMan = Widget.extend({
    template: 'rainbow_man.notification',

    start: function () {
        if (this.data) {
            var data_rainbow_man_type = this.data.rainbowManType ? this.data.rainbowManType : 'medium',
                data_rainbow_man_url = this.data.rainbowManUrl ? this.data.rainbowManUrl : '/web/static/src/img/smile.svg';
            var duration = data_rainbow_man_type == 'fast' ? 2500 : (data_rainbow_man_type == 'medium' ? 3500 : 5000);

            this.$('.o_reward_face').css('background-image', "url('" + data_rainbow_man_url + "')")
            if (this.data.rainbowManMessage) {
                this.$('.o_reward_msg_txt').append(this.data.rainbowManMessage);
            } else {
                this.$('.o_reward_msg_container').remove();
            }
            if (data_rainbow_man_type !== 'no') {
                var self = this;
                this.$el.addClass('o_reward_fading')
                    .animate({display: 'none'},duration,function() {
                        self.$el.remove();
                    });
            };
        };
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @param {Object} action
     * @param {Object} attrs
     */
    prepareData: function (action, attrs) {
        if (!attrs.data_rainbow_man_url) {
            attrs.data_rainbow_man_url = action.rainbow_image_url;
        };
        if (!attrs.data_rainbow_man_message) {
            attrs.data_rainbow_man_message = action.rainbow_message;
        };
        if (!attrs.data_rainbow_man_type) {
            attrs.data_rainbow_man_type = action.rainbow_type;
        };
        this.data = {
            'rainbowManType': attrs.data_rainbow_man_type,
            'rainbowManUrl': attrs.data_rainbow_man_url,
            'rainbowManMessage': attrs.data_rainbow_man_message,
        };
    },
});

return RainbowMan;

});
