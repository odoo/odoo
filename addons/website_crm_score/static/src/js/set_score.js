odoo.define('website_crm_score.set_score', function (require) {
"use strict";

var Model = require('web.Model');
var seo = require('website.seo');
var website = require('website.website');

website.add_template_file('/website_crm_score/static/src/xml/track_page.xml');

seo.Configurator.include({
    track: null,
    start: function() {
        this._super.apply(this, arguments);
        var self = this;
        var obj = website.seo.Configurator.prototype.getMainObject();
        // only display checkbox for website page
        if (obj && obj.model === 'ir.ui.view') {
            this.is_tracked().then(function(data){
                var add = $('<input type="checkbox" required="required"/>');
                if (data[0]['track']) {
                    add.attr('checked','checked');
                    self.track = true;
                }
                else {
                    self.track = false;
                }
                self.$el.find('h3[class="track-page"]').append(add);
            });
        }
    },
    is_tracked: function(val) {
        var obj = seo.Configurator.prototype.getMainObject();
        if (!obj) {
            return $.Deferred().reject();
        } else {
            return new Model(obj.model).call('read', [[obj.id], ['track'], website.get_context()]);
        }
    },
    update: function () {
        var self = this;
        var mysuper = this._super;
        var checkbox_value = this.$el.find('input[type="checkbox"]').is(':checked');
        if (checkbox_value != self.track) {
            this.trackPage(checkbox_value).then(function() {
                mysuper.call(self);
            });
        }
        else {
            mysuper.call(self);
        }
    },
    trackPage: function(val) {
        var obj = seo.Configurator.prototype.getMainObject();
        if (!obj) {
            return $.Deferred().reject();
        } else {
            return new Model(obj.model).call('write', [[obj.id], { track: val }, website.get_context()]);
        }
    },
});

});
