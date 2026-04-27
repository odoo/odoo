/** @odoo-module */

import { useRef, useEffect, useState } from "@odoo/owl";
import { formView } from "@web/views/form/form_view";
import * as formEditorRendererComponents from "@web_studio/client_action/view_editor/editors/form/form_editor_renderer/form_editor_renderer_components";

import { ChatterContainer, ChatterContainerHook } from "../chatter_container";
import { StudioHook } from "@web_studio/client_action/view_editor/editors/components/studio_hook_component";
import { FieldStudio } from "@web_studio/client_action/view_editor/editors/components/field_studio";
import { WidgetStudio } from "@web_studio/client_action/view_editor/editors/components/widget_studio";
import { ViewButtonStudio } from "@web_studio/client_action/view_editor/editors/components/view_button_studio";
import { InnerGroup, OuterGroup } from "./form_editor_groups";
import { AddButtonAction } from "@web_studio/client_action/view_editor/interactive_editor/action_button/action_button";

class Setting extends formView.Renderer.components.Setting {
    static props = {
        ...formView.Renderer.components.Setting.props,
        studioXpath: { type: String, optional: true },
        studioIsVisible: { type: Boolean, optional: true },
    };
}
export class FormEditorRenderer extends formView.Renderer {
    static components = {
        ...formView.Renderer.components,
        ...formEditorRendererComponents,
        Field: FieldStudio,
        Widget: WidgetStudio,
        ViewButton: ViewButtonStudio,
        ChatterContainerHook,
        InnerGroup,
        OuterGroup,
        StudioHook,
        Setting,
        AddButtonAction,
    };
    setup() {
        super.setup();
        const rootRef = useRef("compiled_view_root");
        this.rootRef = rootRef;
        const viewEditorModel = this.env.viewEditorModel;
        this.viewEditorModel = useState(viewEditorModel);
        this.mailComponents.Chatter = ChatterContainer;

        // Deals with invisible modifier by reacting to config.studioShowVisible.
        useEffect(
            (rootEl, showInvisible) => {
                if (!rootEl) {
                    return;
                }
                rootEl.classList.add("o_web_studio_form_view_editor");
                if (showInvisible) {
                    rootEl
                        .querySelectorAll(":not(.o-mail-Form-chatter) .o_invisible_modifier")
                        .forEach((el) => {
                            el.classList.add("o_web_studio_show_invisible");
                            el.classList.remove("o_invisible_modifier");
                        });
                } else {
                    rootEl
                        .querySelectorAll(":not(.o-mail-Form-chatter) .o_web_studio_show_invisible")
                        .forEach((el) => {
                            el.classList.remove("o_web_studio_show_invisible");
                            el.classList.add("o_invisible_modifier");
                        });
                }
            },
            () => [rootRef.el, viewEditorModel.showInvisible]
        );

        // do this in another way?
        useEffect(
            (rootEl) => {
                if (rootEl) {
                    const optCols = rootEl.querySelectorAll("i.o_optional_columns_dropdown_toggle");
                    for (const col of optCols) {
                        col.classList.add("text-muted");
                    }
                }
            },
            () => [rootRef.el]
        );
    }
}
