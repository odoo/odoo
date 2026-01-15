import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { X2ManyField, x2ManyField } from "@web/views/fields/x2many/x2many_field";
import { ListRenderer } from "@web/views/list/list_renderer";


export class FieldMany2ManyAltPOsRenderer extends ListRenderer {
   isCurrentRecord(record) {
      return record.resId === this.props.list.model.root.resId;
  }
}

FieldMany2ManyAltPOsRenderer.recordRowTemplate = "purchase_requisition.AltPOsListRenderer.RecordRow";

export class FieldMany2ManyAltPOs extends X2ManyField {
    static components = {
        ...X2ManyField.components,
        ListRenderer: FieldMany2ManyAltPOsRenderer,
    };

   setup() {
      super.setup();
      this.orm = useService("orm");
      this.action = useService("action");
   }

   get isMany2Many() {
      return true;
   }

   /**
    * Override to: avoid reopening currently open record
    *              open record in same window w/breadcrumb extended
    * @override
    */
   async openRecord(record) {
      if (record.resId !== this.props.record.resId) {
         const action = await this.orm.call(record.resModel, "get_formview_action", [[record.resId]], {
               context: this.props.context,
         });
         await this.action.doAction(action);
      }
   }
}

export const fieldMany2ManyAltPOs = {
    ...x2ManyField,
    component: FieldMany2ManyAltPOs,
};

registry.category("fields").add("many2many_alt_pos", fieldMany2ManyAltPOs);
