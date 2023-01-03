/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";
import { useSetupAction } from "../webclient/actions/action_hook";
import { useLegacyRefs } from "./utils";
import legacyViewRegistry from "web.view_registry";
import { ViewAdapter } from "./action_adapters";
import Widget from "web.Widget";
import {
    breadcrumbsToLegacy,
    getGlobalState,
    getLocalState,
    searchModelStateToLegacy,
} from "./backend_utils";
import { getBundle, loadBundle } from "@web/core/assets";
import { registry } from "@web/core/registry";
import { LegacyComponent } from "./legacy_component";

import { xml, onWillStart } from "@odoo/owl";
const viewRegistry = registry.category("views");

function getJsClassWidget(fieldsInfo) {
    const parsedXML = new DOMParser().parseFromString(fieldsInfo.arch, "text/xml");
    const key = parsedXML.documentElement.getAttribute("js_class");
    return legacyViewRegistry.get(key);
}

const legacyViewTemplate = xml`
    <ViewAdapter Component="Widget" View="View" viewInfo="viewInfo" viewParams="viewParams"
                 widget="widget" onReverseBreadcrumb="onReverseBreadcrumb" selectRecord="props.selectRecord" createRecord="props.createRecord"/>`;

// registers a view from the legacy view registry to the wowl one, but wrapped
// into an Owl Component
function registerView(name, LegacyView) {
    if (viewRegistry.contains(name)) {
        return;
    }
    class Controller extends LegacyComponent {
        setup() {
            this.vm = useService("view");
            this.Widget = Widget; // fool the ComponentAdapter with a simple Widget
            this.View = LegacyView;
            this.viewInfo = {};

            let resIds;
            let searchModel;
            let searchPanel;
            const { globalState } = this.props;
            if (globalState) {
                resIds = globalState.resIds;
                searchModel = searchModelStateToLegacy(globalState.searchModel);
                searchPanel = globalState.searchPanel;
            }

            // always add user context to the action context
            this.user = useService("user");
            const action = Object.assign({}, this.props.action);
            action.context = Object.assign({}, this.user.context, action.context);

            const { actionFlags, breadcrumbs, noBreadcrumbs } = this.env.config;
            if (noBreadcrumbs) {
                action.context.no_breadcrumbs = true;
            }
            this.viewParams = Object.assign({}, actionFlags, {
                action,
                // legacy views automatically add the last part of the breadcrumbs
                breadcrumbs: breadcrumbsToLegacy(breadcrumbs),
                modelName: this.props.resModel,
                currentId: this.props.resId,
                controllerState: {
                    currentId:
                        "resId" in this.props
                            ? this.props.resId
                            : this.props.state && this.props.state.currentId,
                    resIds: this.props.resIds || resIds,
                    searchModel,
                    searchPanel,
                },
            });

            // To open a new empty form view
            // Legacy demands undefined ids, not False
            if (this.viewParams.currentId === false) {
                this.viewParams.currentId = undefined;
                this.viewParams.controllerState.currentId = undefined;
            }

            // Only add mode to viewParams if it is specified to avoid overwriting the default mode in some view (eg graph)
            if (this.props.mode) {
                this.viewParams.mode = this.props.mode;
            }
            const legacyRefs = useLegacyRefs();
            this.widget = this.props.state && this.props.state.__legacy_widget__;
            legacyRefs.widget = this.widget;
            this.onReverseBreadcrumb =
                this.props.state && this.props.state.__on_reverse_breadcrumb__;
            useSetupAction({
                rootRef: {
                    get el() {
                        return legacyRefs.widget && legacyRefs.widget.el;
                    },
                },
                beforeLeave: () => legacyRefs.widget.canBeRemoved(),
                getGlobalState: () => getGlobalState(legacyRefs.component.exportState()),
                getLocalState: () => getLocalState(legacyRefs.component.exportState()),
            });
            onWillStart(this.onWillStart);
        }

        async onWillStart() {
            const params = {
                resModel: this.props.resModel,
                views: this.props.views || this.env.config.views,
                context: this.props.context,
            };
            const options = {
                actionId: this.env.config.actionId,
                loadActionMenus: this.props.loadActionMenus,
                loadIrFilters: this.props.loadIrFilters,
            };
            const viewDescriptions = await this.vm.loadViews(params, options);
            const result = viewDescriptions.__legacy__;
            const fieldsInfo = result.fields_views[this.props.type || this.env.config.viewType];
            const jsClass = getJsClassWidget(fieldsInfo);
            this.View = jsClass || this.View;
            this.viewInfo = Object.assign({}, fieldsInfo, {
                fields: result.fields,
                viewFields: fieldsInfo.fields,
                type: this.props.type || this.env.config.viewType,
            });
            let controlPanelFieldsView;
            if (result.fields_views.search) {
                controlPanelFieldsView = Object.assign({}, result.fields_views.search, {
                    favoriteFilters: result.filters,
                    fields: result.fields,
                    viewFields: result.fields_views.search.fields,
                });
            }
            const { viewSwitcherEntries = [] } = this.env.config;
            const _views = this.viewParams.action.views || this.env.config.views;
            const views = _views
                .filter(([, vtype]) => vtype !== "search")
                .map(([vid, vtype]) => {
                    const view = viewSwitcherEntries.find((v) => v.type === vtype);
                    if (view) {
                        return Object.assign({}, view, { viewID: vid });
                    } else {
                        return {
                            viewID: vid,
                            type: vtype,
                            multiRecord: !legacyView.multiRecord,
                        };
                    }
                });
            this.viewParams.action = Object.assign({}, this.viewParams.action, {
                controlPanelFieldsView,
                _views,
                views,
            });
        }
    }

    Controller.template = legacyViewTemplate;
    Controller.components = { ViewAdapter };
    Controller.isLegacy = true; // for action dialog

    const legacyView = {
        type: LegacyView.prototype.viewType,
        display_name: LegacyView.prototype.display_name,
        icon: LegacyView.prototype.icon,
        isMobileFriendly: LegacyView.prototype.mobile_friendly,
        multiRecord: LegacyView.prototype.multi_record,
        isLegacy: true,
        Controller,
    };
    viewRegistry.add(name, legacyView);
    if (odoo.debug) {
        console.log(`Views: using legacy view: ${name}`);
    }
}

// register views already in the legacy registry, and listens to future registrations
for (const [name, action] of Object.entries(legacyViewRegistry.entries())) {
    registerView(name, action);
}
legacyViewRegistry.onAdd(registerView);

export async function loadLegacyViews() {
    const assets = await getBundle("web.assets_backend_legacy_lazy");
    await loadBundle(assets);
}
