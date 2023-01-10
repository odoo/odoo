/** @odoo-module */

import { registry } from "@web/core/registry";
import { session } from "@web/session";

import { Component } from "@odoo/owl";
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

registry.category("view_widgets").add("res_config_edition", ResConfigEdition);
