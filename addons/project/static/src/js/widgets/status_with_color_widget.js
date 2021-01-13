odoo.define('project.status_with_color', function (require) {
    "use strict";
    
    const fieldRegistry = require('web.field_registry');
    const { FieldMany2One } = require('web.relational_fields');
    const { _lt, qweb } = require('web.core');
    
    /**
     * options :
     * `color_field` : The field that must be use to color the bubble. It must be in the view. (from 0 to 11). Default : grey.
     */
    var StatusWithColor = FieldMany2One.extend({
        _template: 'project.statusWithColor',

        init: function () {
            this._super.apply(this, arguments);
            this.color = this.recordData[this.nodeOptions.color_field];
        },
        
        /**
         * @override
         */
        _renderReadonly() {
            this._super.apply(this, arguments);
            if (this.value) {
                this.$el.prepend(qweb.render(this._template, {
                    color: this.color,
                }));
            }
        },
    });
    
    fieldRegistry.add('status_with_color', StatusWithColor);
    
    return StatusWithColor;
    
});
