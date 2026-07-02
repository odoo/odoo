import { registry } from "@web/core/registry";
import { session } from "@web/session";
import { Setting } from "@web/views/form/setting/setting";

import { Component } from "@odoo/owl";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

class L10nPkEdiResConfigEdition extends Component {
    static template = "l10n_pk_edi_res_config_edition";
    static components = { Setting };
    static props = {
        ...standardWidgetProps,
    };

    setup() {
        const [major, minor] = session.server_version_info;
        this.serverVersion = `${major}.${minor}`;
    }
}

export const l10nPkEdiResConfigEdition = {
    component: L10nPkEdiResConfigEdition,
};

registry.category("view_widgets").add("l10n_pk_edi_res_config_edition", l10nPkEdiResConfigEdition);
