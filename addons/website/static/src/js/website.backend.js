odoo.define('website.backend', function (require) {
"use strict";

var core = require('web.core');
var form_common = require('web.form_common');
var form_widgets = require('web.form_widgets'); // required to guarantee that
    // the overrride of fieldtexthtml works

var WidgetWebsiteButton = form_common.AbstractField.extend({
    template: 'WidgetWebsiteButton',
    render_value: function() {
        this._super();
        this.$el.toggleClass("published", this.get_value() === true);
        if (this.node.attrs.class) {
            this.$el.addClass(this.node.attrs.class);
        }
    },
    is_false: function() {
        return false;
    },
});

core.form_widget_registry.add('website_button', WidgetWebsiteButton);

});
