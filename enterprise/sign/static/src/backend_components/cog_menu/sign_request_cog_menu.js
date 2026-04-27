/** @odoo-module **/

import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

const cogMenuRegistry = registry.category("cogMenu");

/**
 * 'Request signature' menu
 *
 * This component is used to request a signature and link it to a document.
 * @extends Component
 */
export class SignRequestCogMenu extends Component {
    static template = "sign.SignRequestCogMenu";
    static components = { DropdownItem };
    static props = {};

    setup() {
        this.action = useService("action");
    }

    signRequest() {
        /*
         * Fetch resModel from the controller props as it is static until the view changes.
         * Fetch resId from the current state since the state is mutable with newly created records.
         */
        const resModel = this.action.currentController.props.resModel;
        const resId = this.action.currentController.currentState?.resId;
        const referenceDoc = resId && resModel ? `${resModel},${resId}` : false;
        if (referenceDoc) {
            this.action.doAction(
                {
                    name: _t("Signature Request"),
                    type: "ir.actions.act_window",
                    view_mode: "form",
                    views: [[false, "form"]],
                    target: "new",
                    res_model: "sign.send.request",
                },
                {
                    additionalContext: {
                        sign_directly_without_mail: false,
                        default_reference_doc: referenceDoc,
                    },
                }
            );
        }
    }
}

export const SignRequestCogMenuItem = {
    Component: SignRequestCogMenu,
    isDisplayed: async ({ config, searchModel }) => {
        const is_mail_thread = searchModel.searchViewFields?.['message_ids'];
        return (
            searchModel.resModel !== "sign.request" &&
            is_mail_thread &&
            config.viewType === "form" &&
            config.actionType === "ir.actions.act_window"
        );
    },
    groupNumber: 1,
};

cogMenuRegistry.add("sign-request-menu", SignRequestCogMenuItem, { sequence: 10 });
