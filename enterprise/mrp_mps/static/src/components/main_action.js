/** @odoo-module */

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { WithSearch } from "@web/search/with_search/with_search";
import { MainComponent } from '@mrp_mps/components/main';
import { MrpMpsSearchModel } from '@mrp_mps/search/mrp_mps_search_model';
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { Component, onWillStart } from "@odoo/owl";

export class MainComponentAction extends Component {
    static template = "mrp_mps.mrp_mps_action";
    static components = { WithSearch, MainComponent };
    static props = {...standardActionServiceProps};

    setup() {
        this.viewService = useService("view");
        this.resModel = "mrp.production.schedule";

        onWillStart(async () => {
            const views = await this.viewService.loadViews(
                {
                    resModel: this.resModel,
                    context: this.props.action.context,
                    views: [[false, "search"]],
                }
            );
            this.withSearchProps = {
                resModel: this.resModel,
                SearchModel: MrpMpsSearchModel,
                globalState: this.props.globalState,
                context: this.props.action.context,
                domain: this.props.action.domain,
                orderBy: [{name: "id", asc: true}],
                searchMenuTypes: ['filter', 'favorite'],
                searchViewArch: views.views.search.arch,
                searchViewId: views.views.search.id,
                searchViewFields: views.fields,
                loadIrFilters: true
            };
        });
    }
}

registry.category("actions").add("mrp_mps_client_action", MainComponentAction);
