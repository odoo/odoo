odoo.define('mrp.mrp_state', function (require) {

var core = require('web.core');
var common = require('web.form_common');
var _t = core._t;


var SetBulletStatus = common.AbstractField.extend(common.ReinitializeFieldMixin,{
    init: function(field_manager, node) {
        this._super(field_manager, node);
        this.classes = this.options && this.options.classes || {};
    },
    render_value: function() {
        this._super.apply(this, arguments);
        if (this.get("effective_readonly")) {
            var bullet_class = this.classes[this.get('value')] || 'default';
            if (this.get('value')){
                title = this.get('value') == 'waiting'? _t('Waiting Raw Materials.') : _t('Ready to produce.'),
                this.$el.attr('title', title);
                this.$el
                    .removeClass('text-success text-danger text-default')
                this.$el.html($('<span>' + title + '</span>').addClass('label label-' + bullet_class));
            }
        }
    },
});

core.form_widget_registry.add('bullet_state', SetBulletStatus);
});
