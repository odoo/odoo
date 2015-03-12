(function() {
    "use strict";

    var website = openerp.website;
    var _t = openerp._t;

    website.add_template_file('/website_crm_score/static/src/xml/track_page.xml');

    website.seo.Configurator.include({
        track: null,
        start: function() {
            this._super.apply(this, arguments);
            var self = this;
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
        },
        is_tracked: function(val) {
            var obj = website.seo.Configurator.prototype.getMainObject();
            if (!obj) {
                return $.Deferred().reject();
            } else {
                return website.session.model(obj.model).call('read', [[obj.id], ['track'], website.get_context()]);
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
            var obj = website.seo.Configurator.prototype.getMainObject();
            if (!obj) {
                return $.Deferred().reject();
            } else {
                return website.session.model(obj.model).call('write', [[obj.id], { track: val }, website.get_context()]);
            }
        },
    });
})();
