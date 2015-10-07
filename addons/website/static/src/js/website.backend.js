odoo.define('website.backend', function (require) {
"use strict";

var core = require('web.core');
var form_common = require('web.form_common');
var form_widgets = require('web.form_widgets'); // required to guarantee
                                                //  that the overrride of fieldtexthtml works
var _t = core._t;

var WidgetWebsiteButton = form_common.AbstractField.extend({
    template: 'WidgetWebsiteButton',
    render_value: function() {
        this._super.apply(this, arguments);

        var $value = this.$('.o_value');

        if(this.get_value() === true) {
            $value.html(_t('Published'))
                  .removeClass('text-danger')
                  .addClass('text-success');
        } else {
            $value.html(_t('Not Published'))
                  .removeClass('text-success')
                  .addClass('text-danger');
        }

        if(this.node.attrs.class) {
            this.$el.addClass(this.node.attrs.class);
        }
    },
    is_false: function() {
        return false;
    },
});

core.form_widget_registry.add('website_button', WidgetWebsiteButton);

});
