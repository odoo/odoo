/** @odoo-module */
import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { InteractiveEditorSidebar } from "@web_studio/client_action/view_editor/interactive_editor/interactive_editor_sidebar";
import {
    ExistingFields,
    NewFields,
} from "@web_studio/client_action/view_editor/view_structures/view_structures";
import { Property } from "@web_studio/client_action/view_editor/property/property";
import { Properties } from "@web_studio/client_action/view_editor/interactive_editor/properties/properties";
import { ButtonProperties } from "@web_studio/client_action/view_editor/editors/form/form_editor_sidebar/properties/button_properties/button_properties";
import { FieldProperties } from "@web_studio/client_action/view_editor/interactive_editor/properties/field_properties/field_properties";
import { GroupProperties } from "@web_studio/client_action/view_editor/editors/form/form_editor_sidebar/properties/group_properties/group_properties";
import { LabelProperties } from "@web_studio/client_action/view_editor/editors/form/form_editor_sidebar/properties/label_properties/label_properties";
import { PageProperties } from "@web_studio/client_action/view_editor/editors/form/form_editor_sidebar/properties/page_properties/page_properties";
import { _t } from "@web/core/l10n/translation";
import { SidebarViewToolbox } from "@web_studio/client_action/view_editor/interactive_editor/sidebar_view_toolbox/sidebar_view_toolbox";
import { ChatterProperties } from "@web_studio/client_action/view_editor/editors/form/form_editor_sidebar/properties/chatter_properties/chatter_properties";
import { useEditNodeAttributes } from "@web_studio/client_action/view_editor/view_editor_model";

class FormComponents extends Component {
    static template = "web_studio.FormEditor.Sidebar.Components";
    static props = {};

    get structures() {
        return {
            notebook: {
                name: _t("Tabs"),
                class: "o_web_studio_field_tabs",
            },
            group: {
                name: _t("Columns"),
                class: "o_web_studio_field_columns",
            },
        };
    }
}

export class FormEditorSidebar extends Component {
    static template = "web_studio.ViewEditor.FormEditorSidebar";
    static props = {
        openViewInForm: { type: Function, optional: true },
        openDefaultValues: { type: Function, optional: true },
    };
    static components = {
        InteractiveEditorSidebar,
        FormComponents,
        NewFields,
        ExistingFields,
        Property,
        Properties,
        SidebarViewToolbox,
    };

    setup() {
        this.rpc = useService("rpc");
        this.dialog = useService("dialog");
        this.viewEditorModel = useState(this.env.viewEditorModel);
        this.editArchAttributes = useEditNodeAttributes({ isRoot: true });

        this.propertiesComponents = {
            button: {
                component: ButtonProperties,
                props: {
                    availableOptions: ["invisible"],
                },
            },
            field: {
                component: FieldProperties,
                props: {
                    availableOptions: ["invisible", "required", "readonly", "string", "help"],
                },
            },
            group: {
                component: GroupProperties,
            },
            label: {
                component: LabelProperties,
            },
            page: {
                component: PageProperties,
            },
            div: {
                component: ChatterProperties,
            },
        };
    }

    get activeActions() {
        return this.viewEditorModel.controllerProps.archInfo.activeActions;
    }

    getActiveAction(name) {
        return this.activeActions[name] === true;
    }

    onAttributeChanged(value, name) {
        return this.editArchAttributes({ [name]: value });
    }
}
