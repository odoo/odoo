odoo.define('theme_eco_refine.collection_snippet', function (require) {
    var publicWidget = require('web.public.widget');
    publicWidget.registry.collection_snippet = publicWidget.Widget.extend({
        selector: '.ref-collection--container',
        start: function () {
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                self.$('.ref-collection__item').each(function (index) {
                    if (index === 0) {
                        self.$(this).addClass('selected');
                    }
                    self.$(this).on('click', function () {
                        self.$('.ref-collection__item').removeClass('selected');
                        self.$(this).addClass('selected');
                    });
                });
            });
        },
    });
    return publicWidget.registry.collection_snippet;
});
