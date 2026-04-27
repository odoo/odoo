/** @odoo-module */

import { registry } from "@web/core/registry";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { useService, useBus } from "@web/core/utils/hooks";
import { SIZES } from "@web/core/ui/ui_service";
import { Component, useState, useRef, onWillStart } from "@odoo/owl";

class BankConfigureWidget extends Component {
    static template = "account.BankConfigureWidget";
    static props = {
        ...standardWidgetProps,
    }
    setup() {
        this.container = useRef("container");
        this.allInstitutions = [];
        this.state = useState({
            isLoading: true,
            institutions: [],
            gridStyle: "grid-template-columns: repeat(5, minmax(90px, 1fr));"
        });
        this.orm = useService("orm");
        this.action = useService("action");
        this.ui = useService("ui");
        onWillStart(this.fetchInstitutions);
        useBus(this.ui.bus, "resize", this.computeGrid);
    }

    computeGrid() {
        if (this.allInstitutions.length > 4) {
            let containerWidth = this.container.el ? this.container.el.offsetWidth - 32 : 0;
            // when the container width can't be computed, use the screen size and number of journals.
            if (!containerWidth) {
                if (this.ui.size >= SIZES.XXL) {
                    containerWidth = window.innerWidth / (this.props.record.model.root.count < 6 ? 2 : 3);
                } else {
                    containerWidth = Math.max(this.ui.size * 100, 400);
                }
            }
            const canFit = Math.floor(containerWidth / 100);
            const numberOfRows = (Math.floor((this.allInstitutions.length + 1) / 2) >= canFit) + 1;
            this.state.gridStyle = `grid-template-columns: repeat(${canFit}, minmax(90px, 1fr));
                                    grid-template-rows: repeat(${numberOfRows}, 1fr);
                                    grid-auto-rows: 0px;
                                   `;
        }
        this.state.institutions = this.allInstitutions;
    }

    async fetchInstitutions() {
        this.orm.silent.call(this.props.record.resModel, "fetch_online_sync_favorite_institutions", [this.props.record.resId])
        .then((response) => {
            this.allInstitutions = response;
        })
        .finally(() => {
            this.state.isLoading = false;
            this.computeGrid();
        });
    }

    async connectBank(institutionId=null) {
        const action = await this.orm.call("account.online.link", "action_new_synchronization", [[]], {
            preferred_inst: institutionId,
            journal_id: this.props.record.resId,
        })
        this.action.doAction(action);
    }

    async fallbackConnectBank() {
        const action = await this.orm.call('account.online.link', 'create_new_bank_account_action', [], {
            context: {
                active_model: 'account.journal',
                active_id: this.props.record.resId,
            }
        });
        this.action.doAction(action);
    }
}

export const bankConfigureWidget = {
    component: BankConfigureWidget,
}

registry.category("view_widgets").add("bank_configure", bankConfigureWidget);
