import { Component, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { ViewStructures } from "@web_studio/client_action/view_editor/editors/components/view_structures";
import { InteractiveEditorSidebar } from "@web_studio/client_action/view_editor/interactive_editor/interactive_editor_sidebar";
import { ExistingFields } from "@web_studio/client_action/view_editor/editors/components/view_fields";
import { Property } from "@web_studio/client_action/view_editor/property/property";
import { SidebarViewToolbox } from "@web_studio/client_action/view_editor/interactive_editor/sidebar_view_toolbox/sidebar_view_toolbox";
import { Properties } from "@web_studio/client_action/view_editor/interactive_editor/properties/properties";
import { KanbanButtonProperties } from "@web_studio/client_action/view_editor/editors/kanban/kanban_editor_sidebar/properties/kanban_button_properties/kanban_button_properties";
import { FieldProperties } from "@web_studio/client_action/view_editor/interactive_editor/properties/field_properties/field_properties";
import { WidgetProperties } from "@web_studio/client_action/view_editor/interactive_editor/properties/widget_properties/widget_properties";
import { useEditNodeAttributes } from "@web_studio/client_action/view_editor/view_editor_model";
import { fieldsToChoices } from "@web_studio/client_action/view_editor/editors/utils";
import { AsideProperties } from "./properties/aside_properties/aside_properties";
import { FooterProperties } from "./properties/footer_properties/footer_properties";
import { MenuProperties } from "./properties/menu_properties/menu_properties";
import { DivProperties } from "./properties/div_properties/div_properties";

class KanbanFieldProperties extends FieldProperties {
    onChangeAttribute(value, name) {
        if (name === "bold") {
            let cls = this.props.node.attrs.class;
            if (value) {
                cls = cls ? `fw-bold ${cls}` : "fw-bold";
            } else {
                cls = cls
                    .split(" ")
                    .filter((c) => c !== "fw-bold" && c !== "fw-bolder")
                    .join(" ");
            }
            return this.editNodeAttributes({ class: cls });
        }
        return super.onChangeAttribute(...arguments);
    }
}

export class KanbanEditorSidebar extends Component {
    static template = "web_studio.ViewEditor.KanbanEditorSidebar";
    static props = {
        openViewInForm: { type: Function, optional: true },
        openDefaultValues: { type: Function, optional: true },
    };
    static components = {
        InteractiveEditorSidebar,
        ExistingFields,
        Property,
        Properties,
        ViewStructures,
        SidebarViewToolbox,
    };
    static get viewStructures() {
        return {
            aside: {
                name: _t("Side panel"),
                class: "o_web_studio_field_aside",
                isVisible: (vem) => !vem.controllerProps.arch.querySelector("aside"),
            },
            footer: {
                name: _t("Footer"),
                class: "o_web_studio_field_footer",
                isVisible: (vem) => !vem.controllerProps.arch.querySelector("footer"),
            },
            t: {
                name: _t("Menu"),
                class: "o_web_studio_field_menu",
                isVisible: (vem) => !vem.controllerProps.arch.querySelector("t[t-name=menu]"),
            },
            ribbon: {
                name: _t("Ribbon"),
                class: "o_web_studio_field_ribbon",
                isVisible: (vem) =>
                    !vem.controllerProps.arch.querySelector("widget[name=web_ribbon]"),
            },
            kanban_colorpicker: {
                name: _t("Color Picker"),
                class: "o_web_studio_field_color_picker",
                isVisible: (vem) =>
                    !vem.controllerProps.arch.querySelector("field[widget=kanban_color_picker]"),
            },
        };
    }

    setup() {
        this.viewEditorModel = useState(this.env.viewEditorModel);
        this.editArchAttributes = useEditNodeAttributes({ isRoot: true });
        this.propertiesComponents = {
            a: {
                component: KanbanButtonProperties,
            },
            button: {
                component: KanbanButtonProperties,
            },
            field: {
                component: KanbanFieldProperties,
                props: {
                    availableOptions: ["invisible", "string", "bold"],
                },
            },
            aside: {
                component: AsideProperties,
            },
            div: {
                component: DivProperties,
            },
            footer: {
                component: FooterProperties,
            },
            t: {
                component: MenuProperties,
            },
            widget: {
                component: WidgetProperties,
            },
        };
    }

    get archInfo() {
        return this.viewEditorModel.controllerProps.archInfo;
    }

    get colorField() {
        return {
            choices: fieldsToChoices(this.viewEditorModel.fields, ["integer"]),
            required: false,
        };
    }

    get defaultGroupBy() {
        return {
            choices: fieldsToChoices(
                this.viewEditorModel.fields,
                this.viewEditorModel.GROUPABLE_TYPES,
                (field) => field.groupable
            ),
            required: false,
        };
    }

    get defaultOrder() {
        if (this.archInfo.defaultOrder.length >= 1) {
            return this.archInfo.defaultOrder[0];
        } else {
            return { name: "", asc: true };
        }
    }

    get sortChoices() {
        return fieldsToChoices(
            this.viewEditorModel.fields,
            this.viewEditorModel.GROUPABLE_TYPES,
            (field) => field.sortable
        );
    }

    get orderChoices() {
        return [
            { value: "asc", label: _t("Ascending") },
            { value: "desc", label: _t("Descending") },
        ];
    }

    setSortBy(value) {
        this.onSortingChanged(value, this.defaultOrder.asc ? "asc" : "desc");
    }

    setOrder(value) {
        this.onSortingChanged(this.defaultOrder.name, value);
    }

    onSortingChanged(sortBy, order) {
        if (sortBy) {
            this.editAttribute(`${sortBy} ${order}`, "default_order");
        } else {
            this.editAttribute("", "default_order");
        }
    }

    editAttribute(value, name) {
        return this.editArchAttributes({ [name]: value });
    }

    editDefaultGroupBy(value) {
        this.editAttribute(value || "", "default_group_by");
    }

    editColor(value) {
        if (value && !this.viewEditorModel.fieldsInArch.includes(value)) {
            this.viewEditorModel.doOperation({
                type: "add",
                target: {
                    tag: "kanban",
                },
                position: "inside",
                node: {
                    attrs: {
                        name: value,
                        invisible: "1",
                    },
                    tag: "field",
                },
            });
        }
        this.editAttribute(value || "", "highlight_color");
    }
}
