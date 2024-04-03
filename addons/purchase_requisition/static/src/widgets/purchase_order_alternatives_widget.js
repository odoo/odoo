/** @odoo-module */

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { X2ManyField } from "@web/views/fields/x2many/x2many_field";
import { ListRenderer } from "@web/views/list/list_renderer";


export class FieldMany2ManyAltPOsRenderer extends ListRenderer {
   isCurrentRecord(record) {
      return record.data.id === this.env.model.root.data.id;
  }
}

FieldMany2ManyAltPOsRenderer.recordRowTemplate = "purchase_requisition.AltPOsListRenderer.RecordRow";

export class FieldMany2ManyAltPOs extends X2ManyField {
   setup() {
      this.orm = useService("orm");
      this.action = useService("action");
      // TODO: this is a terrible hack, make this a proper extension of many2many if/when possible
      this.props.record.activeFields[this.props.name].widget = "many2many";
      super.setup();
   }

   /**
    * Override to: avoid reopening currently open record
    *              open record in same window w/breadcrumb extended
    * @override
    */
   async openRecord(record) {
      if (record.data.id !== this.props.record.data.id) {
         const action = await this.orm.call(record.resModel, "get_formview_action", [[record.data.id]], {
               context: this.props.context,
         });
         await this.action.doAction(action);
      }
   }
}

FieldMany2ManyAltPOs.components = {
   ...X2ManyField.components,
   ListRenderer: FieldMany2ManyAltPOsRenderer,
};

registry.category("fields").add("many2many_alt_pos", FieldMany2ManyAltPOs);
