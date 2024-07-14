/** @odoo-module */

import { Component, onWillStart, onWillUpdateProps, useState } from "@odoo/owl";
import { CheckBox } from "@web/core/checkbox/checkbox";
import { DomainSelectorDialog } from "@web/core/domain_selector_dialog/domain_selector_dialog";
import { SelectMenu } from "@web/core/select_menu/select_menu";
import { Property } from "@web_studio/client_action/view_editor/property/property";
import { useService } from "@web/core/utils/hooks";
import { Record } from "@web/model/record";
import { Many2OneField } from "@web/views/fields/many2one/many2one_field";
import { Many2ManyTagsField } from "@web/views/fields/many2many_tags/many2many_tags_field";
import { LimitGroupVisibility } from "@web_studio/client_action/view_editor/interactive_editor/properties/limit_group_visibility/limit_group_visibility";
import { RainbowEffect } from "./rainbow_effect";
import { SidebarPropertiesToolbox } from "@web_studio/client_action/view_editor/interactive_editor/properties/sidebar_properties_toolbox/sidebar_properties_toolbox";
import { useEditNodeAttributes } from "@web_studio/client_action/view_editor/view_editor_model";
import { useSnackbarWrapper } from "@web_studio/client_action/view_editor/view_editor_hook";
import { ModifiersProperties } from "@web_studio/client_action/view_editor/interactive_editor/properties/modifiers/modifiers_properties";

export class ButtonProperties extends Component {
    static template = "web_studio.ViewEditor.InteractiveEditorProperties.Button";
    static props = {
        node: { type: Object },
        availableOptions: { type: Array, optional: true },
    };
    static components = {
        CheckBox,
        LimitGroupVisibility,
        Many2OneField,
        Many2ManyTagsField,
        RainbowEffect,
        Record,
        SelectMenu,
        Property,
        SidebarPropertiesToolbox,
        ModifiersProperties,
    };

    setup() {
        this.dialog = useService("dialog");
        this.orm = useService("orm");
        this.rpc = useService("rpc");
        this.state = useState({});
        this.editNodeAttributes = useEditNodeAttributes();

        this.decoratedOrmCall = useSnackbarWrapper(this.orm.call.bind(this.orm));
        this.decoratedOrmWrite = useSnackbarWrapper(this.orm.write.bind(this.orm));

        const m2mFieldsToFetch = {
            display_name: { type: "char" },
        };
        const approvalRecordDefinition = {
            group_id: {
                type: "many2one",
                relation: "res.groups",
            },
            responsible_id: {
                type: "many2one",
                relation: "res.users",
                domain: [["share", "=", false]],
            },
            users_to_notify: {
                type: "many2many",
                relation: "res.users",
                related: { activeFields: m2mFieldsToFetch, fields: m2mFieldsToFetch },
            },
        };
        this.recordProps = {
            resModel: "studio.approval.rule",
            fields: approvalRecordDefinition,
            activeFields: approvalRecordDefinition,
        };

        onWillStart(() => {
            if (this.props.node.attrs.studio_approval) {
                this.updateApprovalSpec();
            }
        });

        onWillUpdateProps((nextProps) => {
            if (nextProps.node.attrs.studio_approval) {
                this.updateApprovalSpec(this.getApprovalParams(nextProps.node));
            } else {
                delete this.state.approvalSpec;
            }
        });
    }

    onChangeAttribute(value, name) {
        return this.editNodeAttributes({ [name]: value });
    }

    async onChangeApprovalRecord(record, changes, id) {
        await this.decoratedOrmWrite("studio.approval.rule", [id], changes);
        this.updateApprovalSpec();
    }

    onEnableApproval(enable) {
        this.env.viewEditorModel.doOperation({
            enable,
            type: "enable_approval",
            btn_name: this.props.node.attrs.name,
            btn_type: this.props.node.attrs.type,
            btn_string: this.props.node.attrs.string,
            model: this.env.viewEditorModel.controllerProps.resModel,
            view_id: this.env.viewEditorModel.view.id,
        });
    }

    get showRainbowMan() {
        const attrs = this.props.node.attrs;
        return attrs.class !== "oe_stat_button" && attrs.type === "object";
    }

    get isApprovalEnabled() {
        return this.props.node.attrs.studio_approval === "True";
    }

    async createApprovalRule() {
        const params = this.getApprovalParams();
        params[3] = this.props.node.attrs.string;
        await this.decoratedOrmCall("studio.approval.rule", "create_rule", params);
        this.updateApprovalSpec();
    }

    getApprovalParams(node = this.props.node) {
        let method,
            action = false;
        if (node.attrs.type === "object") {
            method = node.attrs.name;
        } else {
            action = node.attrs.name;
        }
        return [this.env.viewEditorModel.resModel, method, action];
    }

    async getApprovalSpec(approvalParams) {
        return await this.orm.call("studio.approval.rule", "get_approval_spec", approvalParams);
    }

    async onApprovalArchive(id) {
        await this.decoratedOrmWrite("studio.approval.rule", [id], {
            active: false,
        });
        this.updateApprovalSpec();
    }

    async onApprovalEdit(name, id, value) {
        const isMethod = this.props.node.attrs.type === "object";
        await this.rpc("/web_studio/edit_approval", {
            model: this.env.viewEditorModel.resModel,
            method: isMethod ? this.props.node.attrs.name : false,
            action: isMethod ? false : this.props.node.attrs.name,
            operations: [[name, id, value]],
        });
        this.updateApprovalSpec();
    }

    onApprovalSelectDomain(id) {
        const domain = this.state.approvalSpec.rules.find((r) => r.id === id).domain;
        this.dialog.add(DomainSelectorDialog, {
            resModel: this.env.viewEditorModel.resModel,
            domain: JSON.stringify(domain || []),
            isDebugMode: !!this.env.debug,
            onConfirm: async (domain) => {
                await this.decoratedOrmWrite("studio.approval.rule", [id], {
                    domain,
                });
                this.updateApprovalSpec();
            },
        });
    }

    async onChangeNotificationOrder(ev, id) {
        await this.decoratedOrmWrite("studio.approval.rule", [id], {
            notification_order: ev.target.value,
        });
        this.updateApprovalSpec();
    }

    async updateApprovalSpec(params = this.getApprovalParams()) {
        this.state.approvalSpec = await this.getApprovalSpec(params);
        this.env.viewEditorModel.env.bus.trigger("approval-update");
    }
}
