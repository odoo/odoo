/** @odoo-module */

import { registry } from "@web/core/registry"
import { listView } from "@web/views/list/list_view"
import { ListController } from "@web/views/list/list_controller"

class ResPartnerListController extends ListController {
    setup(){
        super.setup()
        console.log("this is res partner controller")
    }
}

export const resPartnerListView = {
    ...listView,
    Controller: ResPartnerListController,
    buttonTemplate: "owl.ResPartnerListView.Buttons",
}

registry.category("views").add("res_partner_list_view", resPartnerListView)