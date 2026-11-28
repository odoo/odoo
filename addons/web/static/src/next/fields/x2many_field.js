import { Component, t } from "@odoo/owl";
import { ListRenderer } from "../list_view/list_renderer";
import { fieldRegistry, useField } from "./field";

/**
 * The records of a one2many or a many2many, as a list: the columns are the
 * fields of the list sub-view of the field node.
 */
export class X2ManyField extends Component {
    static template = "web.next.X2ManyField";
    static components = { ListRenderer };

    field = useField(t.array());
}

fieldRegistry.add("one2many", X2ManyField).add("many2many", X2ManyField);
