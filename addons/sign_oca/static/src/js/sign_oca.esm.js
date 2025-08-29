/** @odoo-module */

import {FormController} from "@web/views/form/form_controller";
import {ListController} from "@web/views/list/list_controller";
import {_t} from "@web/core/l10n/translation";
import {patch} from "@web/core/utils/patch";
const {onWillStart} = owl;
import {useService} from "@web/core/utils/hooks";
import {user} from "@web/core/user";

export function patchControllerSignOca() {
    return {
        setup() {
            super.setup(...arguments);
            this.user = user;
            this.orm = useService("orm");
            this.action = useService("action");
            this.showSignOcaTemplateGenerateMulti = false;
            onWillStart(async () => {
                return Promise.all([this._showSignOcaTemplateGenerateMulti()]);
            });
        },
        async _showSignOcaTemplateGenerateMulti() {
            var sign_oca_group_user = await this.user.hasGroup(
                "sign_oca.sign_oca_group_user"
            );
            if (sign_oca_group_user) {
                await this.orm
                    .call("sign.oca.template", "search_count", [
                        [["model", "=", this.props.resModel]],
                    ])
                    .then((templateCount) => {
                        this.showSignOcaTemplateGenerateMulti = templateCount !== 0;
                    });
            }
        },
        async _actionSignOcaTemplateGenerateMulti() {
            var resIds = "";
            if (this.getSelectedResIds) resIds = await this.getSelectedResIds();
            else resIds = this.props.resId;
            this.action.doAction(
                "sign_oca.sign_oca_template_generate_multi_act_window",
                {
                    additionalContext: {
                        model: this.props.resModel,
                        active_ids: resIds,
                    },
                    on_close: () => {
                        this.update({}, {reload: false});
                    },
                }
            );
        },
        get actionMenuItems() {
            const menuItems = super.actionMenuItems;
            if (menuItems && this.showSignOcaTemplateGenerateMulti) {
                menuItems.action.push({
                    key: "sign",
                    description: _t("Sign from template"),
                    callback: () => this._actionSignOcaTemplateGenerateMulti(),
                    icon: "fa fa-pencil",
                });
            }
            return menuItems;
        },
    };
}

patch(ListController.prototype, patchControllerSignOca());
patch(FormController.prototype, patchControllerSignOca());
