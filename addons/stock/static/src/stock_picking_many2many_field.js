import { X2ManyField, x2ManyField } from "@web/views/fields/x2many/x2many_field";
import { useService } from "@web/core/utils/hooks";
import { useSelectCreate } from "@web/views/fields/relational_utils";
import { registry } from "@web/core/registry";


class BatchToPickingMany2ManyField extends X2ManyField {
    setup() {
        super.setup();
        this.orm = useService("orm");
        const selectCreate = useSelectCreate({
            resModel: "stock.picking",
            activeActions: this.activeActions,
            onSelected: async (resIds) => {
                const addToWaveWizard = await this.orm.create("stock.add.to.wave", [{
                    wave_id: this.props.record.resId,
                    picking_ids: resIds,
                }]);
                const action = await this.orm.call("stock.add.to.wave", "attach_pickings", [addToWaveWizard[0]], {context: {from_wave_form: true}});
                this.action.doAction(action);
            },
            onCreateEdit: () => this.createOpenRecord(),
        });
        this.selectCreate = (params) => {
            const p = Object.assign({}, params);
            const currentIds = this.props.record.data[this.props.name].currentIds.filter(
                (id) => typeof id === "number"
            );
            p.domain = [...(p.domain || []), "!", ["id", "in", currentIds]];
            return selectCreate(p);
        };
    }

    get isMany2Many() {
        return true;
    }
}

export const batchToPickingMany2ManyField = {
    ...x2ManyField,
    component: BatchToPickingMany2ManyField,
};

registry.category("fields").add("stock_picking_many2many", batchToPickingMany2ManyField);
