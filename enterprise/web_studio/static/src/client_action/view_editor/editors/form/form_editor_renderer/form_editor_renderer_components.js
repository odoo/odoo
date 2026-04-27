/** @odoo-module */

import { formView } from "@web/views/form/form_view";
import { StudioHook } from "@web_studio/client_action/view_editor/editors/components/studio_hook_component";
import { NewButtonBoxDialog } from "@web_studio/client_action/view_editor/editors/form/form_editor_sidebar/properties/button_properties/new_button_box_dialog";
import { FieldSelectorDialog } from "@web_studio/client_action/view_editor/editors/components/field_selector_dialog";
import { SelectionContentDialog } from "@web_studio/client_action/view_editor/interactive_editor/field_configuration/selection_content_dialog";
import {
    randomName,
    studioIsVisible,
    useStudioRef,
} from "@web_studio/client_action/view_editor/editors/utils";
import { _t } from "@web/core/l10n/translation";
import { useOwnedDialogs } from "@web/core/utils/hooks";

import { Component, useState, useRef } from "@odoo/owl";
import { AddButtonAction } from "../../../interactive_editor/action_button/action_button";

/**
 * Overrides and extensions of components used by the FormRenderer
 * As a rule of thumb, elements should be able to handle the props
 * - studioXpath: the xpath to the node in the form's arch to which the component
 *   refers
 * - They generally be clicked on to change their characteristics (in the Sidebar)
 * - The click doesn't trigger default behavior (the view is inert)
 * - They can be draggable (FormLabel referring to a field)
 * - studioIsVisible: all components whether invisible or not, are compiled and rendered
 *   this props allows to toggle the class o_invisible_modifier
 * - They can have studio hooks, that are placeholders for dropping content (new elements, field, or displace elements)
 */

const components = formView.Renderer.components;

/*
 * FormLabel:
 * - Can be draggable if in InnerGroup
 */
export class FormLabel extends components.FormLabel {
    static template = "web_studio.FormLabel";
    static props = {
        ...components.FormLabel.props,
        studioXpath: String,
        studioIsVisible: { type: Boolean, optional: true },
    };
    setup() {
        super.setup();
        useStudioRef("rootRef", this.onClick);
    }
    get className() {
        let className = super.className;
        if (!studioIsVisible(this.props)) {
            className += " o_web_studio_show_invisible";
        }
        className += " o-web-studio-editor--element-clickable";
        return className;
    }
    onClick(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        this.env.config.onNodeClicked(this.props.studioXpath);
    }
}

/*
 * Notebook:
 * - Display every page, the elements in the page handle whether they are invisible themselves
 * - Push a droppable hook on every empty page
 * - Can add a new page
 */
export class Notebook extends components.Notebook {
    static template = "web_studio.Notebook.Hook";
    static components = { ...components.Notebook.components, StudioHook };
    static props = {
        ...components.Notebook.props,
        studioIsVisible: { type: Boolean, optional: true },
        studioXpath: String,
    };

    setup() {
        this.viewEditorModel = useState(this.env.viewEditorModel);
        super.setup();
    }
    computePages(props) {
        const pages = super.computePages(props);
        pages.forEach((p) => {
            p[1].studioIsVisible = p[1].isVisible;
            p[1].isVisible = p[1].isVisible || this.viewEditorModel.showInvisible;
        });
        return pages;
    }
    onNewPageClicked() {
        const vem = this.viewEditorModel;
        const node = {
            tag: "page",
            attrs: {
                string: _t("New Page"),
                name: randomName("studio_page"),
            },
        };
        vem.doOperation({
            type: "add",
            node,
            target: vem.getFullTarget(this.props.studioXpath),
            position: "inside",
        });
    }
}

export class StatusBarButtons extends components.StatusBarButtons {
    static template = `web_studio.FormViewAddButtonAction`;
    static components = {
        ...components.StatusBarButtons.components,
        AddButtonAction,
    };
}

export class StatusBarFieldHook extends Component {
    static template = "web_studio.AddElementHook";
    static props = {
        addStatusBar: { type: Boolean },
    };
    setup() {
        this.addDialog = useOwnedDialogs();
    }
    get classNames() {
        return "o_web_studio_statusbar_hook";
    }
    get title() {
        return _t("Add a pipeline status bar");
    }
    onClick() {
        this.addDialog(SelectionContentDialog, {
            defaultChoices: [
                ["status1", _t("First Status")],
                ["status2", _t("Second Status")],
                ["status3", _t("Third Status")],
            ],
            onConfirm: (choices) => {
                const viewEditorModel = this.env.viewEditorModel;
                if (this.props.addStatusBar) {
                    viewEditorModel.pushOperation({ type: "statusbar" });
                }

                const target = {
                    tag: "header",
                };
                const subViewXpath = viewEditorModel.getSubviewXpath();
                if (subViewXpath) {
                    target.subview_xpath = subViewXpath;
                }

                viewEditorModel.doOperation({
                    type: "add",
                    target,
                    position: "inside",
                    node: {
                        attrs: {
                            widget: "statusbar",
                            options: "{'clickable': '1'}",
                        },
                        field_description: {
                            default_value: true,
                            field_description: _t("Pipeline status bar"),
                            model_name: viewEditorModel.resModel,
                            name: randomName(`x_studio_selection_field`),
                            selection: JSON.stringify(choices),
                            type: "selection",
                        },
                        tag: "field",
                    },
                });
            },
        });
    }
}

export class AvatarHook extends Component {
    static template = "web_studio.AddElementHook";
    static props = { fields: Object };
    setup() {
        this.addDialog = useOwnedDialogs();
    }
    get classNames() {
        return "oe_avatar ms-3 o_web_studio_avatar";
    }
    get title() {
        return _t("Add Picture");
    }
    onClick() {
        const fields = [];
        for (const field of Object.values(this.props.fields)) {
            if (field.type === "binary") {
                fields.push(field);
            }
        }
        this.addDialog(FieldSelectorDialog, {
            fields,
            showNew: true,
            onConfirm: (field) => {
                this.env.viewEditorModel.doOperation({
                    type: "avatar_image",
                    field,
                });
            },
        });
    }
}

export class ButtonHook extends Component {
    static template = "web_studio.AddElementHook";
    static props = {
        add_buttonbox: { type: Boolean, optional: true },
        studioIsVisible: { type: Boolean, optional: true },
    };
    setup() {
        this.addDialog = useOwnedDialogs();
    }
    get classNames() {
        return "oe_stat_button o_web_studio_button_hook flex-grow-1 flex-lg-grow-0 fa fa-plus-square";
    }
    get tooltip() {
        return _t("Add a button");
    }
    onClick() {
        this.addDialog(NewButtonBoxDialog, {
            model: this.env.viewEditorModel,
            isAddingButtonBox: Boolean(this.props.add_buttonbox),
        });
    }
}

export class ButtonBox extends components.ButtonBox {
    static template = "web_studio.ButtonBox";
    static components = {};
    static props = {
        ...components.ButtonBox.props,
        studioIsVisible: { type: Boolean, optional: true },
    };

    setup() {
        super.setup();
        this.togglerRef = useRef("toggleRef");
        this.viewEditorModel = useState(this.env.viewEditorModel);
        this.expanded = useState({ value: false });
    }

    toggle() {
        this.expanded.value = !this.expanded.value;
        this.togglerRef.el.classList.toggle("show", this.expanded.value);
        this.togglerRef.el.ariaExpanded = this.expanded.value;
    }

    isSlotVisible(slot) {
        if (this.viewEditorModel.isEditingSubview) {
            return false;
        }
        return this.viewEditorModel.showInvisible || super.isSlotVisible(slot);
    }
}
