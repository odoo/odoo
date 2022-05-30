/** @odoo-module **/

import { FieldOne2Many } from 'web.relational_fields';
import ListRenderer from 'web.ListRenderer';
import fieldRegistry from 'web.field_registry';
import {_t} from 'web.core';

//----------------------------------------------------

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
            this.displayNotification({ message: _t('Please click on the "save" button first'), type: 'danger' });
            return;
        }
        this.do_action({
            name: _t('Select Operations to Copy'),
            type: 'ir.actions.act_window',
            res_model: 'mrp.routing.workcenter',
            views: [[false, 'list'], [false, 'form']],
            domain: ['|', ['bom_id', '=', false], ['bom_id.active', '=', true]],
            context: {
                tree_view_ref: 'mrp.mrp_routing_workcenter_copy_to_bom_tree_view',
                bom_id: this.recordData.id,
            },
        });

    },
});

fieldRegistry.add('mrp_one2many_with_copy', MrpFieldOne2ManyWithCopy);

export default MrpFieldOne2ManyWithCopy;
