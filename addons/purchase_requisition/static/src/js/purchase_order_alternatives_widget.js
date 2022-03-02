/** @odoo-module **/

import field_registry from 'web.field_registry';
import { FieldMany2Many } from 'web.relational_fields';
import PurchaseOrderCompareListRenderer from '@purchase_requisition/js/purchase_order_compare_list_renderer';

const FieldMany2ManySameWindow = FieldMany2Many.extend({

    /**
     * @override
     */
     init: function (parent, name, record, options) {
        this._super(...arguments);
        this.isMany2Many = true;
     },

    /**
     * Override to ensure we can't unlink a PO from itself (i.e. confusing behavior)
     * @override
     */
     _getRenderer: function () {
        if (this.view.arch.tag === 'tree') {
            return PurchaseOrderCompareListRenderer;
        }
        return this._super(...arguments);
    },

    /**
     * Override to open record in same window w/breadcrumb extended
     * @override
     */
    _onOpenRecord: function (ev) {
        ev.stopPropagation();
        const targetId = ev.target.state.data.find(obj => {
            return obj.id === ev.data.id;
        }).res_id;
        // don't re-open current record
        if (targetId !== this.record.res_id) {
            this._rpc({
                model: this.model,
                method: 'get_formview_action',
                args: [[targetId]],
                context: this.record.getContext(this.recordParams),
                domain: this.record.getDomain(this.recordParams),
            }).then(action => {
                this.trigger_up('do_action', {action: action});
            });
        }
    }
});

field_registry.add('many2many_same_window', FieldMany2ManySameWindow);
