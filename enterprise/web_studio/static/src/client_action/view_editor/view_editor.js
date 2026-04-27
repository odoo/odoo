/** @odoo-module */
import { Component, onWillUpdateProps, useState, useSubEnv, useRef, markRaw } from "@odoo/owl";

import { useBus, useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { StudioView } from "@web_studio/client_action/view_editor/studio_view";

import { InteractiveEditor } from "./interactive_editor/interactive_editor";
import { useViewEditorModel } from "./view_editor_hook";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { getDefaultConfig } from "@web/views/view";

import { XmlResourceEditor } from "@web_studio/client_action/xml_resource_editor/xml_resource_editor";
import { useSetupAction } from "@web/search/action_hook";
import { _t } from "@web/core/l10n/translation";

class ViewXmlEditor extends XmlResourceEditor {
    static props = { ...XmlResourceEditor.props, studioViewArch: { type: String } };
    setup() {
        super.setup();
        this.viewEditorModel = this.env.viewEditorModel;
        useBus(this.viewEditorModel.bus, "error", () => this.render(true));
        this.studioViewState = useState({ arch: this.props.studioViewArch });

        onWillUpdateProps((nextProps) => {
            if (nextProps.studioViewArch !== this.props.studioViewArch) {
                const studioResource = this.getStudioResource(this.state.resourcesOptions);
                if (studioResource) {
                    studioResource.value.arch = nextProps.studioViewArch;
                }
            }
        });
    }

    getStudioResource(resourcesOptions) {
        return resourcesOptions.find((opt) => opt.value.id === this.viewEditorModel.studioViewId);
    }
}

export class ViewEditor extends Component {
    static props = { ...standardActionServiceProps };
    static components = { StudioView, InteractiveEditor, ViewXmlEditor };
    static template = "web_studio.ViewEditor";

    static displayName = _t("View Editor");

    setup() {
        /* Services */
        this.studio = useService("studio");
        this.orm = useService("orm");
        /* MISC */
        // Avoid pollution from the real actionService's env
        // Set config compatible with View.js
        useSubEnv({ config: getDefaultConfig() });

        // Usefull for drag/drop
        this.rootRef = useRef("root");
        this.rendererRef = useRef("viewRenderer");

        const initialState = {};
        const breadcrumbs = this.env.editionFlow.breadcrumbs;
        if (breadcrumbs.length) {
            initialState.showInvisible = breadcrumbs[0].initialState.showInvisible;
            initialState.activeNodeXpath = breadcrumbs.at(-1).initialState.activeNodeXpath;
        }

        this.viewEditorModel = useViewEditorModel(this.rendererRef, { initialState });

        useSetupAction({
            getLocalState: () => {
                // Use this as a hook that is triggered when the actionService knows
                // this component will be unmounted, is still alive and the new action
                // is being built.
                // We store the state in the breadcrumbs, because there two ways
                // to respawn the editor:
                // - the editor's breadcrumbs
                // - the standard actionService breadcrumbs
                const breadcrumbs = this.viewEditorModel.breadcrumbs;
                breadcrumbs[0].initialState = markRaw({
                    showInvisible: this.viewEditorModel.showInvisible,
                });
                const last = breadcrumbs.at(-1);
                last.initialState = markRaw({
                    ...(last.initialState || {}),
                    activeNodeXpath: this.viewEditorModel.activeNodeXpath,
                });
            },
        });
    }

    get interactiveEditorKey() {
        const { viewType, breadcrumbs } = this.viewEditorModel;
        let key = viewType;
        if (breadcrumbs.length > 1) {
            key += `_${breadcrumbs.length}`;
        }
        return key;
    }

    onSaveXml({ resourceId, oldCode, newCode }) {
        this.viewEditorModel.doOperation({
            type: "replace_arch",
            viewId: resourceId,
            oldArch: oldCode,
            newArch: newCode,
        });
    }

    onXmlEditorClose() {
        this.viewEditorModel.switchMode();
    }
}
registry.category("actions").add("web_studio.view_editor", ViewEditor);
