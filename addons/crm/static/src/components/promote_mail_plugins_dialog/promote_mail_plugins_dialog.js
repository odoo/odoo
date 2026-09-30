import { Dialog } from "@web/core/dialog/dialog";
import { Component, useProps, t } from "@odoo/owl";
import { DocumentationLink } from "@web/core/documentation_link/documentation_link";

export class PromoteMailPluginsDialog extends Component {
    static template = "crm.PromoteMailPluginsDialog";
    static components = { Dialog, DocumentationLink };
    props = useProps({
        title: t.string(),
    });
}
