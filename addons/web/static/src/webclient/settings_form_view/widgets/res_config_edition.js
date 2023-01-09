/** @odoo-module */

import { registry } from "@web/core/registry";
import { session } from "@web/session";
import { Setting } from "@web/webclient/settings_form_view/settings/setting";

import { Component } from "@odoo/owl";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
const { DateTime } = luxon;

/**
 * Widget in the settings that handles a part of the "About" section.
 * Contains info about the odoo version, database expiration date and copyrights.
 */
class ResConfigEdition extends Component {
    setup() {
        this.serverVersion = session.server_version;
        this.expirationDate = session.expiration_date
            ? DateTime.fromSQL(session.expiration_date).toLocaleString(DateTime.DATE_FULL)
            : DateTime.now().plus({ days: 30 }).toLocaleString(DateTime.DATE_FULL);
    }
}

ResConfigEdition.template = "res_config_edition";
ResConfigEdition.components = { Setting };
ResConfigEdition.props = {
    ...standardWidgetProps,
};
registry.category("view_widgets").add("res_config_edition", ResConfigEdition);
