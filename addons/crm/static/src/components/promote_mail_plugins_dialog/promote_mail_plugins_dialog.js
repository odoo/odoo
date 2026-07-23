import { Dialog } from "@web/core/dialog/dialog";
import { Component, t, useProps } from "@odoo/owl";

export class PromoteMailPluginsDialog extends Component {
    static template = "crm.PromoteMailPluginsDialog";
    static components = { Dialog };
    props = useProps({
        title: t.string(),
    });
}
