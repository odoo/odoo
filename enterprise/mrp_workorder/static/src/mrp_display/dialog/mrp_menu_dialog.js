/** @odoo-module */

import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { MrpWorkcenterDialog } from "./mrp_workcenter_dialog";
import { MrpQualityCheckSelectDialog } from "./mrp_check_select_dialog";

import { Component, useState } from "@odoo/owl";

export class MrpMenuDialog extends Component {
    static props = {
        close: Function,
        groups: Object,
        params: Object,
        record: Object,
        reload: Function,
        title: String,
        removeFromCache: Function,
    };
    static template = "mrp_workorder.MrpDisplayMenuDialog";
    static components = { Dialog };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.dialogService = useService("dialog");
        this.notification = useService("notification");
        this.state = useState({ menu: "main"});
    }

    async callAction(method, props = {}) {
        const action = await this.orm.call(this.props.record.resModel, method,
            [
                [this.props.record.resId],
            ],
            {
                context: {from_shop_floor: true}
            }
        );
        this.action.doAction(action, {
            onClose: async () => {
                await this.props.reload(this.props.record);
            },
            props,
        });
        this.props.close();
    }

    async callAddComponentAction() {
        return this.callAction("action_add_component", {
            onCatalogUpdated: async () => {
                await this.props.reload(this.props.record);
            },
        });
    }

    moveToWorkcenter() {
        function _moveToWorkcenter(workcenters) {
            const workcenter = workcenters[0];
            this.props.record.update(
                { workcenter_id: [workcenter.id, workcenter.display_name] },
            );
            this.props.record.save();
            this.props.removeFromCache(this.props.record.resId);
            this.props.close();
        }
        const params = {
            title: _t("Select a new work center"),
            confirm: _moveToWorkcenter.bind(this),
            radioMode: true,
            workcenters: this.props.params.workcenters.filter(
                (w) => w[0] != this.props.record.data.workcenter_id[0]
            ),
        };
        this.dialogService.add(MrpWorkcenterDialog, params);
    }

    openMO() {
        const id = this.props.record.resModel === 'mrp.production' ?
            this.props.record.resId : this.props.record.data.production_id[0];
        this.action.doAction({
            'type': 'ir.actions.act_window',
            'res_model': 'mrp.production',
            'views': [[false, 'form']],
            'res_id': id,
        });
        this.props.close();
    }

    block() {
        const options = {
            additionalContext: { default_workcenter_id: this.props.record.data.workcenter_id[0] },
            onClose: async () => {
                await this.props.reload();
            }
        };
        this.action.doAction('mrp.act_mrp_block_workcenter_wo', options);
        this.props.close();
    }

    unblock() {
        this.action.doActionButton({
            type: "object",
            resId: this.props.record.data.workcenter_id[0],
            name: "unblock",
            resModel: "mrp.workcenter",
            onClose: async () => {
                await this.props.reload();
            }
        });
        this.props.close();
    }

    displayMainMenu(){
        this.state.menu = "main";
    }

    displayInstructionsMenu(){
        this.state.menu = "instructions";
    }

    displayImprovementMenu(){
        this.state.menu = "improvement";
    }

    updateStep(){
        this.proposeChange('update_step');
    }

    async addStep(){
        if (this.props.params.checks?.length > 0) {
            this.proposeChange('add_step');
        } else {
            await this.proposeChangeForCheck('add_step', null);
        }
    }

    removeStep(){
        this.proposeChange('remove_step');
    }

    setPicture(){
        this.proposeChange('set_picture');
    }

    proposeChange(type){
        let title = _t("Select the step you want to modify");
        if(type == 'add_step') {
            title = _t("Indicate after which step you would like to add this one");
        }
        const params = {
            title,
            confirm: this.proposeChangeForCheck.bind(this),
            checks: this.props.params.checks,
            type,
        };
        this.dialogService.add(MrpQualityCheckSelectDialog, params);
    }

    async proposeChangeForCheck(type, check) {
        let action;
        if (type === 'add_step'){
            if (check) {
                await this.orm.write("mrp.workorder", [this.props.record.resId], { current_quality_check_id: check.id });
            }
            action = await this.orm.call(
                "mrp.workorder",
                "action_add_step",
                [[this.props.record.resId]],
            );
        } else {
            action = await this.orm.call(
                "mrp.workorder",
                "action_propose_change",
                [[this.props.record.resId], type, check.id],
            );
        }
        await this.action.doAction(action, {
            onClose: async () => {
                await this.props.reload(this.props.record);
                if (type === 'remove_step') {
                    this.notification.add(_t("Your suggestion to delete the %s step was succesfully created.", check.display_name),
                        { type: "success", }
                    );
                }
            }
        });
        this.props.close();
    }
}
