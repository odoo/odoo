odoo.define('project.status_with_color', function (require) {
    "use strict";
    
    const fieldRegistry = require('web.field_registry');
    const { FieldMany2One } = require('web.relational_fields');
    const { _lt, qweb } = require('web.core');
    
    var StatusWithColor = FieldMany2One.extend({
        _template: 'project.statusWithColor',

        willStart: function(){
            const promises = [];
            promises.push(this._super.apply(this, arguments));
            if(this.mode !== 'edit'){
                promises.push(this._loadWidgetDataReadonly());
            }
            return Promise.all(promises);
        },

        
        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------
        _loadWidgetDataReadonly: function(){
            var self = this;
            return this._rpc({
                model: this.value.model,
                method: 'search_read',
                fields: ['id', 'color'],
                domain: [['id', '=', this.value.res_id]],
            }).then(data => {
                self.color = data[0].color;
            });
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
