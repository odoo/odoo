/** @odoo-module **/
import fieldRegistry from 'web.field_registry';
import {FieldMany2One} from 'web.relational_fields';

const OpenMoveWidget = FieldMany2One.extend({
    events: Object.assign({}, FieldMany2One.prototype.events, {
        'click': '_onOpenMove',
    }),
    _onOpenMove: function(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        var self = this;
        this._rpc({
            model: 'account.move.line',
            method: 'open_move',
            args: [this.res_id],
        }).then(function (actionData){
            return self.do_action(actionData);
        });
    },
});
fieldRegistry.add('open_move_widget', OpenMoveWidget);
