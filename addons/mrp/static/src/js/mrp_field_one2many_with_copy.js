odoo.define('mrp.MrpFieldOne2ManyWithCopy', function (require) {

"use strict";

var FieldOne2Many = require('web.relational_fields').FieldOne2Many;
var ListRenderer = require('web.ListRenderer');
var fieldRegistry = require('web.field_registry');
const {_t} = require('web.core');

//----------------------------------------------------
var dialogs = require('web.view_dialogs');

var MrpFieldOne2ManyWithCopyListRenderer = ListRenderer.extend({

    /**
     * @override
     */
    init: function (parent, state, params) {
        this._super.apply(this, arguments);
        this.creates.push({
            string: parent.nodeOptions.copy_text,
            context: '',
        });
    },
});

var MrpFieldOne2ManyWithCopy = FieldOne2Many.extend({

    /**
     * @override
     */
    init: function (parent, name, record, options) {
        this._super.apply(this, arguments);
        this.nodeOptions = _.defaults(this.nodeOptions, {
            copy_text: _t('Copy Existing Operations'),
        });
    },
    /**
     * @override
     */
    _getRenderer: function () {
        if (this.view.arch.tag === 'tree') {
            return MrpFieldOne2ManyWithCopyListRenderer;
        }
        return this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    _openFormDialog: function (params) {
        if (params.context === undefined) {
            return this._super.apply(this, arguments);
        }
        const parent = this.getParent();
        const parentIsNew = parent.state.res_id === undefined;
        const parentHasChanged = parent.state.isDirty();
        if (parentIsNew || parentHasChanged) {
            this.do_warn(false, _t('Please click on the "save" button first'));
            return;
        }
        var self = this;
        this.do_action({
            name: _t('Select Operations to Copy'),
            type: 'ir.actions.act_window',
            res_model: 'mrp.routing.workcenter',
            views: [[false, 'list']],
            context: {
                tree_view_ref: 'mrp.mrp_routing_workcenter_copy_to_bom_tree_view',
                bom_id: this.recordData.id,
            },
            target: 'new',
        }, {
            on_close: function () {
                self.trigger_up('reload');
        }
        });

    },
});

fieldRegistry.add('mrp_one2many_with_copy', MrpFieldOne2ManyWithCopy);

return MrpFieldOne2ManyWithCopy;

});
