odoo.define('mail.ComposeSelectButton', function (require) {
"use strict";

var core = require('web.core');
var form_common = require('web.form_common');
var form_widgets = require('web.form_widgets'); // required to guarantee
                                                //  that the overrride of fieldtexthtml works
var _t = core._t;

var ComposeSelectButton = form_widgets.FieldBoolean.extend({
    template: 'mail.ComposeSelectButton',
    events: {
        'click': 'set_toggle'
    },
    render_value: function () {
        this._super.apply(this, arguments);

        var $value = this.$('.o_value');
        if(this.get_value() === false) {
            $value.html(_t('click here'))
        }else {
            $value.html(_t('click here'))
        }

        if(this.node.attrs.class) {
            this.$el.addClass(this.node.attrs.class);
        }
    },
    set_toggle: function () {
        var self = this;
        var toggle_value = !this.get_value();
        this.set_value(toggle_value);
    }, 
});

core.form_widget_registry.add('select_all', ComposeSelectButton);

return {
    ComposeSelectButton: ComposeSelectButton
  };
});
