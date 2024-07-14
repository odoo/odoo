/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart } from "@odoo/owl";

class MainComponent extends Component {
	setup() {
        const links = JSON.parse(browser.localStorage.getItem("odoo-iot-linked_reports"));
		const report_list = links ? Object.keys(links) : [];
		this.orm = useService("orm");
		onWillStart(async () => {
			let report_ids = await this.orm
				.searchRead(
					"ir.actions.report",
					[["id", "in", report_list]],
				)
			this.report_list = report_ids;
		});
	}
	removeFromLocal(id) {
        const links = JSON.parse(browser.localStorage.getItem("odoo-iot-linked_reports"));
        delete links[id]
        if (Object.keys(links).length == 0)
            // If the list is empty, remove the entry
            browser.localStorage.removeItem("odoo-iot-linked_reports");
        else
            // Replace the entry in LocalStorage by the same object with the key 'id' removed
            browser.localStorage.setItem("odoo-iot-linked_reports", JSON.stringify(links))
        window.location.reload();
	}
}

MainComponent.template = 'iot.delete_printer';

registry.category("actions").add("iot_delete_linked_devices_action", MainComponent);

export default MainComponent;
