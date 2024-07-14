/** @odoo-module */

import { registry } from "@web/core/registry";
import { registerCleanup } from "@web/../tests/helpers/cleanup";
import { MainComponentsContainer } from "@web/core/main_components_container";
import { resetViewCompilerCache } from "@web/views/view_compiler";
import { MockServer } from "@web/../tests/helpers/mock_server";

// Services
import { systrayItem } from "@web_studio/systray_item/systray_item";
import { ormService } from "@web/core/orm_service";
import { fieldService } from "@web/core/field_service";
import { nameService } from "@web/core/name_service";
import { homeMenuService } from "@web_enterprise/webclient/home_menu/home_menu_service";
import { studioService, useStudioServiceAsReactive } from "@web_studio/studio_service";
import { actionService } from "@web/webclient/actions/action_service";
import { menuService } from "@web/webclient/menus/menu_service";
import { hotkeyService } from "@web/core/hotkeys/hotkey_service";
import { viewService } from "@web/views/view_service";
import { companyService } from "@web/webclient/company_service";
import { dialogService } from "@web/core/dialog/dialog_service";
import { notificationService } from "@web/core/notifications/notification_service";
import { popoverService } from "@web/core/popover/popover_service";

import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import {
    mount,
    editSelect,
    editSelectMenu,
    getFixture,
    patchWithCleanup,
} from "@web/../tests/helpers/utils";
import { ViewEditor } from "@web_studio/client_action/view_editor/view_editor";
import { Component, useSubEnv, xml } from "@odoo/owl";

import { EditionFlow } from "@web_studio/client_action/editor/edition_flow";
import { useService } from "@web/core/utils/hooks";
import { makeFakeLocalizationService } from "@web/../tests/helpers/mock_services";
import { useOwnDebugContext } from "@web/core/debug/debug_context";
import { commandService } from "@web/core/commands/command_service";

export function selectorContains(target, selector, contains) {
    const elems = Array.from(target.querySelectorAll(selector)).filter((el) =>
        el.textContent.includes(contains)
    );
    return elems.length !== 1 ? null : elems[0];
}
/**
 * Gets the displayed value of a select wether it's
 * an actual HTML select or a SelectMenu.
 */
export function valueOfSelect(target, selector) {
    const el = target.querySelector(selector);
    if (!el) {
        throw new Error(`ValueOfSelect error: No element matches "${selector}".`);
    }

    if (el.tagName === "SELECT") {
        return el.options[el.selectedIndex].value;
    } else if (el.classList.contains("o_select_menu")) {
        return el.querySelector(":scope .o_select_menu_toggler_slot").innerText;
    } else {
        throw new Error(
            `ValueOfSelect error: "${selector}" is neither an HTML select nor a SelectMenu.`
        );
    }
}

export function createMockViewResult(serverData, viewType, arch, model) {
    return {
        models: flattenModels(serverData.models),
        views: {
            [viewType]: {
                arch: arch,
                model: model,
            },
        },
    };
}

export function editAnySelect(el, selector, value) {
    const target = el.querySelector(selector);
    if (!target) {
        throw new Error(`EditAnySelect could not find any element for "${selector}".`);
    }
    if (target.tagName === "SELECT") {
        return editSelect(el, selector, value);
    } else if (target.classList.contains("o_select_menu")) {
        return editSelectMenu(el, selector, value);
    }
}

export function disableHookAnimation(target) {
    target.querySelectorAll(".o_web_studio_hook_separator").forEach((sep) => {
        sep.style.setProperty("transition", "none", "important");
    });
}

export function registerViewEditorDependencies() {
    registry.category("systray").add("StudioSystrayItem", systrayItem);

    const serviceRegistry = registry.category("services");
    serviceRegistry.add("orm", ormService);
    serviceRegistry.add("field", fieldService);
    serviceRegistry.add("name", nameService);
    serviceRegistry.add("home_menu", homeMenuService);
    serviceRegistry.add("menu", menuService);
    serviceRegistry.add("studio", studioService);
    serviceRegistry.add("action", actionService);
    serviceRegistry.add("view", viewService);
    serviceRegistry.add("dialog", dialogService);
    serviceRegistry.add("notification", notificationService);
    serviceRegistry.add("popover", popoverService);
    serviceRegistry.add("hotkey", hotkeyService);
    serviceRegistry.add("command", commandService);
    serviceRegistry.add("localization", makeFakeLocalizationService(), { force: true });

    serviceRegistry.add("company", companyService);
    serviceRegistry.add("messaging", makeFakeMessagingService());

    registerCleanup(() => resetViewCompilerCache());
}

class ViewEditorHoc extends Component {
    static template = xml`<ViewEditor action="{}" className="''" />`;
    static components = { ViewEditor };
    setup() {
        const editionFlow = new EditionFlow(this.env, {
            rpc: useService("rpc"),
            dialog: useService("dialog"),
            studio: useStudioServiceAsReactive(),
            view: useService("view"),
        });
        useSubEnv({
            editionFlow,
        });
        if (this.env.debug) {
            useOwnDebugContext();
        }
    }
}

class ViewEditorParent extends Component {
    static components = { ViewEditorHoc, MainComponentsContainer };
    static props = {};
    static template = xml`
        <MainComponentsContainer />
        <div class="o_studio">
            <div class="o_web_studio_editor">
                <div class="o_action_manager">
                    <div class="o_web_studio_editor_manager d-flex flex-row w-100 h-100">
                        <ViewEditorHoc />
                    </div>
                </div>
            </div>
        </div>
    `;
}

/**
 * @typedef {Object} CreateViewEditorResult
 * @property {Element} target
 * @property {ViewEditor} viewEditor
 */

/**
 * @returns {CreateViewEditorResult}
 */
export async function createViewEditor({ arch, serverData = {}, mockRPC, resModel, type, resId }) {
    const actionToEdit = { res_model: resModel };
    const currentViewId = 99999999;
    if (type && arch) {
        serverData.views = serverData.views || {};
        serverData.views[`${resModel},${currentViewId},${type}`] = arch;
        actionToEdit.views = [[currentViewId, type]];
    }

    const searchRegex = new RegExp(`^${resModel},\w*,search$`); // eslint-disable-line no-useless-escape
    const viewsHaveSearch = Object.keys(serverData.views || {}).some((k) => searchRegex.test(k));
    if (!viewsHaveSearch) {
        serverData.views[`${resModel},false,search`] = "<search />";
    }

    // Little hack, edit_view_arch takes the studio_view_id in its arguments
    // but will return the full arch just as the edit_view_route does.
    // this intercepts the call and changes the args in place to simulate that (not-so-good)-API
    if (mockRPC && typeof mockRPC === "function") {
        const _mockRPC = mockRPC;
        mockRPC = (route, args) => {
            const res = _mockRPC(route, args);
            if (route === "/web_studio/edit_view_arch") {
                args.view_id = currentViewId;
            }
            return res;
        };
    }

    const mountTarget = getFixture();

    const env = await makeTestEnv({
        serverData,
        mockRPC: createMockRPC(mockRPC),
    });
    env.services.studio.setParams({
        viewType: type,
        editorTab: "views",
        action: actionToEdit,
        controllerState: {
            resId,
        },
    });

    return await mount(ViewEditorParent, mountTarget, { env });
}

function flattenModels(models) {
    const flattenModels = {};
    for (const modelName in models) {
        const newModel = {};
        flattenModels[modelName] = newModel;

        const fields = models[modelName].fields;
        for (const fieldName in fields) {
            newModel[fieldName] = fields[fieldName];
        }
    }
    return flattenModels;
}

function createMockRPC(customRouteHandler) {
    if (typeof customRouteHandler === "function") {
        return customRouteHandler;
    } else if (typeof customRouteHandler === "object") {
        const routeHandler = {
            "/web_studio/get_studio_view_arch": () => ({ studio_view_arch: "" }),
            "/web_studio/edit_view": () => ({}),
            "/web_studio/edit_view_arch": () => ({}),
            ...customRouteHandler,
        };

        return function (route, args) {
            if (route in routeHandler) {
                return routeHandler[route](route, args);
            }
        };
    }
}

export function makeArchChanger() {
    let mockServer = null;
    patchWithCleanup(MockServer.prototype, {
        init() {
            super.init(...arguments);
            mockServer = this;
        },
    });

    return (viewId, arch) => {
        const viewDescr = mockServer._getViewFromId(viewId);
        mockServer.archs[viewDescr.key] = arch;
    };
}

function makeFakeMessagingService() {
    const chatter = {
        update: () => {},
        refresh: () => {},
        exists: () => {},
        delete: () => {},
        thread: {},
    };

    const messaging = {
        models: {
            Chatter: {
                insert: () => chatter,
            },
        },
    };

    const service = {
        get: () => messaging,
        modelManager: {
            messaging,
            messagingCreatedPromise: new Promise((resolve) => resolve()),
            startListening: () => {},
            stopListening: () => {},
            removeListener: () => {},
        },
    };

    return {
        start(env) {
            return service;
        },
    };
}
