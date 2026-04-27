/** @odoo-module **/
import { Component, EventBus, onWillDestroy, useState, useSubEnv, xml } from "@odoo/owl";

import { registry } from "@web/core/registry";
import { makeActionManager } from "@web/webclient/actions/action_service";
import { useBus, useService } from "@web/core/utils/hooks";

import { StudioActionContainer } from "./studio_action_container";
import { EditorMenu } from "./editor_menu/editor_menu";

import { AppMenuEditor } from "./app_menu_editor/app_menu_editor";
import { NewModelItem } from "./new_model_item/new_model_item";
import { EditionFlow } from "./edition_flow";
import { useStudioServiceAsReactive } from "@web_studio/studio_service";
import { useSubEnvAndServices, useServicesOverrides } from "@web_studio/client_action/utils";
import { omit } from "@web/core/utils/objects";

class DialogWithEnv extends Component {
    static template = xml`<t t-component="props.Component" t-props="componentProps" />`;
    static props = ["*"];

    setup() {
        useSubEnvAndServices(this.props.env);
    }

    get componentProps() {
        const additionalProps = omit(this.props, "Component", "env", "componentProps");
        return { ...this.props.componentProps, ...additionalProps };
    }
}
const dialogService = {
    dependencies: ["dialog"],
    start(env, { dialog }) {
        function addDialog(Component, _props, options) {
            const props = { env, Component, componentProps: _props };
            return dialog.add(DialogWithEnv, props, options);
        }
        return { ...dialog, add: addDialog };
    },
};

const actionServiceStudio = {
    dependencies: ["studio", "dialog"],
    start(env, { studio }) {
        const router = {
            current: { hash: {} },
            pushState() {},
            hideKeyFromUrl: () => {},
        };
        const action = makeActionManager(env, router);
        const _doAction = action.doAction;

        async function doAction(actionRequest, options) {
            if (actionRequest === "web_studio.action_edit_report") {
                return studio.setParams({
                    editedReport: options.report,
                });
            }
            return _doAction(...arguments);
        }

        return Object.assign(action, { doAction });
    },
};

const menuButtonsRegistry = registry.category("studio_navbar_menubuttons");
export class Editor extends Component {
    static template = "web_studio.Editor";
    static props = {};
    static components = {
        EditorMenu,
        StudioActionContainer,
    };

    static menuButtonsId = 1;
    setup() {
        const globalBus = this.env.bus;
        const newBus = new EventBus();
        useBus(globalBus, "CLEAR-UNCOMMITTED-CHANGES", (ev) =>
            newBus.trigger("CLEAR-UNCOMMITTED-CHANGES", ev.detail)
        );
        useBus(globalBus, "MENUS:APP-CHANGED", (ev) =>
            newBus.trigger("MENUS:APP-CHANGED", ev.detail)
        );
        newBus.addEventListener("CLEAR-CACHES", () => globalBus.trigger("CLEAR-CACHES"));

        useSubEnv({
            bus: newBus,
        });

        useServicesOverrides({
            dialog: dialogService,
            action: actionServiceStudio,
        });
        this.studio = useService("studio");

        const editionFlow = new EditionFlow(this.env, {
            dialog: useService("dialog"),
            studio: useStudioServiceAsReactive(),
            view: useService("view"),
        });
        useSubEnv({
            editionFlow,
        });

        this.actionService = useService("action");

        this.state = useState({ actionContainerId: 1 });
        useBus(this.studio.bus, "UPDATE", async () => {
            this.state.actionContainerId++;
        });

        // Push instance-specific components in the navbar. Because we want those elements
        // immediately, we add them at setup time, not onMounted.
        // Also, because they are Editor instance-specific, and that Destroyed is mostly called
        // after the new instance is created, we need to remove the old entries before adding the new ones
        menuButtonsRegistry.getEntries().forEach(([name]) => {
            if (name.startsWith("app_menu_editor_") || name.startsWith("new_model_item_")) {
                menuButtonsRegistry.remove(name);
            }
        });
        const menuButtonsId = this.constructor.menuButtonsId++;
        menuButtonsRegistry.add(`app_menu_editor_${menuButtonsId}`, {
            Component: AppMenuEditor,
            props: { env: this.env },
        });
        menuButtonsRegistry.add(`new_model_item_${menuButtonsId}`, { Component: NewModelItem });
        onWillDestroy(() => {
            menuButtonsRegistry.remove(`app_menu_editor_${menuButtonsId}`);
            menuButtonsRegistry.remove(`new_model_item_${menuButtonsId}`);
        });
    }

    switchView({ viewType }) {
        this.studio.setParams({ viewType, editorTab: "views" });
    }
    switchViewLegacy(ev) {
        this.studio.setParams({ viewType: ev.detail.view_type });
    }

    switchTab({ tab }) {
        this.studio.setParams({ editorTab: tab });
    }
}
