odoo.define('website_crm_referral.referral_widget', function (require) {
    "use strict";



var ReferralWidget = require('website_sale_referral.referral_widget');
var core = require('web.core');
var QWeb = core.qweb;


ReferralWidget.include({
    events: _.extend({}, ReferralWidget.prototype.events, {
        'click #create_lead' : 'onclick_submit'
    }),

    onclick_submit: function(ev) {
        if(this.check_form_validity()) {
            var self = this;
            this.onclick_common(ev, function(data) {
                var params = self.get_params(ev);
                self.empty_form();
                self.inject_tracking(params);
            });
        }
    },

    check_form_validity: function() {
        var required_empty_input = false;
        $("input:required").each( function(index, item) {
            if(item.value === '') {
                $(item).addClass('is-invalid');
                required_empty_input = true;
            }
            else {
                $(item).removeClass('is-invalid');
            }
        });

        var invalid_email = false;
        $("input[type='email']:required").each(function(index, item) {
            var email = item.value;
            if(email != '') {
                var atpos = email.indexOf("@");
                var dotpos = email.lastIndexOf(".");
                if (atpos<1 || dotpos<atpos+2 || dotpos+2>=email.length) { //invalid
                    $(item).addClass('is-invalid');
                    invalid_email = true;
                }
                else {
                    $(item).removeClass('is-invalid');
                }
            }
        });

        return !invalid_email && !required_empty_input;
    },

    empty_form:function() {
        $("input[name='name']")[0].value = '';
        $("input[name='email']")[0].value = '';
        $("input[name='phone']")[0].value = '';
        $("input[name='company']")[0].value = '';
        $("textarea[name='comment']")[0].value = '';
    },

    get_params:function(ev) {
        var params = this._super.apply(this, arguments);
        params.name = $("input[name='name']").val();
        params.email = $("input[name='email']").val();
        params.phone = $("input[name='phone']").val();
        params.company = $("input[name='company']").val();
        params.comment = $("textarea[name='comment']").val();
        return params;
    },

    inject_tracking: function(params) {
        if(this.is_demo_data) {
            var referrals = {};
            referrals[params.email] = {'name': params.name, 'company': params.company, 'state': 'new'};
            this.render_tracking(referrals);
            this.is_demo_data = false;
        }
        else {
            var rendered_html = QWeb.render('referral_tracking_single_sub_template', {'r':{
                'name': params.name,
                'company': params.company,
                'state': 'new',
                'iso_date': moment.utc().format("YYYY-MM-DD HH:mm:ss"),
                'date_str':moment.utc().format("l")
            }});
            var old_html = $("div[id='referral_tracking_single_sub_template']").html();
            $("div[id='referral_tracking_single_sub_template']").html(rendered_html.concat(old_html));
            
            var potential_reward = $("div[id='potential_reward']");
            potential_reward.html(this.reward_value_to_text(++this.referrals_count - this.referrals_won));
        }
    },

});

});
