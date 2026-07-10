import { Dialog } from "@web/core/dialog/dialog";
import { Component, props, t } from "@odoo/owl";

export class PromoteMailPluginsDialog extends Component {
    static template = "crm.PromoteMailPluginsDialog";
    static components = { Dialog };
    props = props({
        title: t.string(),
    });
}
