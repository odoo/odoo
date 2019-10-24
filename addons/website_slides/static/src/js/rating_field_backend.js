odoo.define('website_slides.ratingField', function (require) {
"use strict";

var basicFields = require('web.basic_fields');
var fieldRegistry = require('web.field_registry');

var core = require('web.core');

var QWeb = core.qweb;

var FieldFloatRating = basicFields.FieldFloat.extend({
    xmlDependencies: !basicFields.FieldFloat.prototype.xmlDependencies ?
        ['/portal_rating/static/src/xml/portal_tools.xml'] : basicFields.FieldFloat.prototype.xmlDependencies.concat(
            ['/portal_rating/static/src/xml/portal_tools.xml']
        ),
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     * @private
     */
    _render: function () {
        var self = this;

        return Promise.resolve(this._super()).then(function () {
            self.$el.html(QWeb.render('portal_rating.rating_stars_static', {
                'val': self.value / 2,
                'inline_mode': true
            }));
        });
    },
});

fieldRegistry.add('field_float_rating', FieldFloatRating);

return {
    FieldFloatRating: FieldFloatRating,
};

});
