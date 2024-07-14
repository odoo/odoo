/** @odoo-module */

import { ViewButton } from "@web/views/view_button/view_button";
import { ViewCompiler } from "@web/views/view_compiler";
import { patch } from "@web/core/utils/patch";

import { StudioApproval } from "@web_studio/approval/studio_approval";
import { useApproval } from "@web_studio/approval/approval_hook";
import { useSubEnv } from "@odoo/owl";

patch(ViewCompiler.prototype, {
    compileButton(el, params) {
        const button = super.compileButton(...arguments);
        const studioApproval = el.getAttribute("studio_approval") === "True";
        if (studioApproval) {
            button.setAttribute("studioApproval", studioApproval);
        }
        return button;
    },
});

patch(ViewButton.prototype, {
    setup() {
        super.setup(...arguments);
        if (this.props.studioApproval) {
            let { type, name } = this.props.clickParams;
            if (type && type.endsWith("=")) {
                type = type.slice(0, -1);
            }
            const action = type === "action" && name;
            const method = type === "object" && name;
            this.approval = useApproval({
                getRecord: (props) => props.record,
                action,
                method,
            });

            const onClickViewButton = this.env.onClickViewButton;
            useSubEnv({
                onClickViewButton: (params) => {
                    if (params.clickParams.type === "action") {
                        // if the button is an action then we check the approval client side
                        params.beforeExecute = this.checkBeforeExecute.bind(this);
                    }
                    onClickViewButton(params);
                },
            });
        }
    },
    async checkBeforeExecute() {
        this.approval.willCheck = true;
        if (!this.approval.resId) {
            const model = this.props.record.model;
            const rec = "resId" in model.root ? model.root : this.props.record;
            await rec.save();
        } else if (this.props.record && this.props.record.isDirty) {
            await this.props.record.save();
        }
        return this.approval.checkApproval();
    },
});

ViewButton.props.push("studioApproval?");
ViewButton.components = Object.assign(ViewButton.components || {}, { StudioApproval });
