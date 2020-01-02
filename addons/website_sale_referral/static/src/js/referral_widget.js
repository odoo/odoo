odoo.define('website_sale_referral.referral_widget', function (require) {
    "use strict";

var publicWidget = require('web.public.widget');
var core = require('web.core');
var QWeb = core.qweb;
var _t = core._t;

publicWidget.registry.ReferralWidget = publicWidget.Widget.extend({
    xmlDependencies: ['/website_sale_referral/static/src/xml/referral_tracking_sub_template.xml'],
    selector:'.referral_widget',
    events: {
        'click .share_social_network': 'onclick_share_social_network',
        'click .get_link' : 'onclick_get_link',
    },

    start: function() {
        this.load_tracking();
        return this._super.apply(this, arguments);
    },

    load_tracking: function() {
        var token = $("input[name='referral_token']").val();
        var url = token ? '/referral/tracking/'.concat(token) : '/referral/tracking/';
        var self = this;
        this._rpc({
            route:url
        }).then(function (data) {
            self.currency_symbol = data.currency_symbol;
            self.currency_position = data.currency_position;
            self.reward_value = data.reward_value;
            var referrals = 'my_referrals' in data ? data.my_referrals : {};
            self.render_tracking(referrals);
        });
    },

    render_tracking: function(data) {
        var referrals = data;
        this.is_demo_data = false;
        if(Object.keys(referrals).length == 0) {
            referrals = this.get_sample_referral_statuses();
            this.currency_symbol = '$';
            this.currency_position = 'before';
            this.reward_value = 200;
            this.is_demo_data = true;
        }
        this.referrals_count = Object.keys(referrals).length;
        this.referrals_won = 0;
        var r;
        for(r in referrals) {
            if(referrals[r].state == 'done') {
                this.referrals_won++;
            }
        }

        for(r in referrals) {
            referrals[r].date_str = moment.utc(referrals[r].iso_date).format("l"); //iso8601 parsing
        }
        var context = {
            'my_referrals': referrals,
            'total_reward': this.reward_value_to_text(this.referrals_won),
            'potential_reward': this.reward_value_to_text(this.referrals_count - this.referrals_won)
        };
        var rendered_html = QWeb.render('referral_tracking_sub_template', context);
        if(this.is_demo_data) {
            rendered_html = "<div class='o_sample_overlay bg-white'/>".concat(rendered_html);
        }
        $("div[id='referral_tracking_sub_template']").html(rendered_html);
    },

    reward_value_to_text: function(quantity) {
        if(this.currency_position == 'after') {
            return (quantity * this.reward_value).toString().concat(this.currency_symbol);
        }
        else {
            return this.currency_symbol.concat((quantity * this.reward_value).toString());
        }
    },

    get_sample_referral_statuses: function() {
    //This is not demo data, this is a dummy to show as an example on the referral register page
        return {
            'julie@example.com': {
                'state': 'in_progress',
                'name': 'Julie Richards',
                'company': 'Ready Mat',
                'iso_date': moment.utc().add(-1, 'hours').format()
            },
            'brandon@example.com': {
                'state': 'new',
                'name': 'Brandon Freeman',
                'company': 'Azure Interior',
                'iso_date': moment.utc().add(-1, 'days').format()
            },
            'collen@example.com': {
                'state': 'in_progress',
                'name': 'Colleen Diaz',
                'company': 'Azure Interior',
                'iso_date': moment.utc().add(-1, 'days').format()
            },
            'kevin@example.com': {
                'state': 'done',
                'name': 'Kevin Leblanc',
                'company': 'Azure Interior',
                'iso_date': moment.utc().add(-2, 'days').format()
            },
            'lucille@example.com': {
                'state': 'cancel',
                'name': 'Lucille Camarero',
                'company': 'Ready Mat',
                'iso_date': moment.utc().add(-2, 'days').format()
            }
        };
    },


    onclick_share_social_network: function(ev) {
        this.onclick_common(ev, function(data) {
            window.open(data.link);
        });
    },

    onclick_get_link: function(ev) {
        this.onclick_common(ev, function(data) {
            var input = $("input[id='copy_link_input']")[0], btn = $("#copy-link");
            btn.html("<i class='fa fa-lg fa-check pr-2' role='img'/>Link Copied");
            btn.addClass("bg-primary");
            btn.removeClass("bg-700");
            input.value = data.link;
            input.select();
            document.execCommand("copy");
        });
    },

    onclick_common: function(ev, then_func) {
        this._rpc({
            route:'/referral/send',
            params:this.get_params(ev)
        }).then(function (data) {
            then_func(data);
        });
    },

    get_params:function(ev) {
        var params = {};
        params.token = $("input[name='referral_token']").val();
        params.channel = ev.target.closest('button').value;
        return params;
    },
});

return publicWidget.registry.ReferralWidget;

});
