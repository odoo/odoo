/** @odoo-module **/
const { Component, hooks, tags } = owl;

import { useService } from "../core/service_hook";
import { useSetupAction } from "../webclient/actions/action_hook";
import legacyViewRegistry from "web.view_registry";
import { ViewAdapter } from "./action_adapters";
import Widget from "web.Widget";
import { breadcrumbsToLegacy } from "./utils";
import { setScrollPosition } from "../core/utils/scrolling";
import { registry } from "@web/core/registry";

const viewRegistry = registry.category("views");

function getJsClassWidget(fieldsInfo) {
    const parsedXML = new DOMParser().parseFromString(fieldsInfo.arch, "text/xml");
    const key = parsedXML.documentElement.getAttribute("js_class");
    return legacyViewRegistry.get(key);
}

const legacyViewTemplate = tags.xml`
    <ViewAdapter Component="Widget" View="View" viewInfo="viewInfo" viewParams="viewParams"
                 widget="widget" onReverseBreadcrumb="onReverseBreadcrumb" t-ref="controller"
                 t-on-scrollTo.stop="onScrollTo"/>`;

// registers a view from the legacy view registry to the wowl one, but wrapped
// into an Owl Component
function registerView(name, LegacyView) {
    class Controller extends Component {
        constructor() {
            super(...arguments);
            this.vm = useService("view");
            this.controllerRef = hooks.useRef("controller");
            this.Widget = Widget; // fool the ComponentAdapter with a simple Widget
            this.View = LegacyView;
            this.viewInfo = {};
            this.viewParams = Object.assign({}, this.props.actionFlags, {
                action: this.props.action,
                // legacy views automatically add the last part of the breadcrumbs
                breadcrumbs: breadcrumbsToLegacy(this.props.breadcrumbs),
                modelName: this.props.resModel,
                currentId: this.props.resId,
                controllerState: {
                    currentId:
                        "resId" in this.props
                            ? this.props.resId
                            : this.props.state && this.props.state.currentId,
                    resIds: this.props.resIds || (this.props.state && this.props.state.resIds),
                    searchModel:
                        this.props.searchModel ||
                        (this.props.state && this.props.state.searchModel),
                    searchPanel:
                        this.props.searchPanel ||
                        (this.props.state && this.props.state.searchPanel),
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
            this.widget = this.props.state && this.props.state.__legacy_widget__;
            this.onReverseBreadcrumb =
                this.props.state && this.props.state.__on_reverse_breadcrumb__;
            useSetupAction({
                beforeLeave: () => this.controllerRef.comp.__widget.canBeRemoved(),
                exportState: () => this.controllerRef.comp.exportState(),
            });
            this.onScrollTo = (ev) => {
                setScrollPosition(this, { left: ev.detail.left, top: ev.detail.top });
            };
        }

        async willStart() {
            const params = {
                resModel: this.props.resModel,
                views: this.props.views,
                context: this.props.context,
            };
            const options = {
                actionId: this.props.actionId,
                loadActionMenus: this.props.loadActionMenus,
                loadIrFilters: this.props.loadIrFilters,
            };
            const viewDescriptions = await this.vm.loadViews(params, options);
            const result = viewDescriptions.__legacy__;
            const fieldsInfo = result.fields_views[this.props.type];
            const jsClass = getJsClassWidget(fieldsInfo);
            this.View = jsClass || this.View;
            this.viewInfo = Object.assign({}, fieldsInfo, {
                fields: result.fields,
                viewFields: fieldsInfo.fields,
            });
            let controlPanelFieldsView;
            if (result.fields_views.search) {
                controlPanelFieldsView = Object.assign({}, result.fields_views.search, {
                    favoriteFilters: result.filters,
                    fields: result.fields,
                    viewFields: result.fields_views.search.fields,
                });
            }
            const views = this.viewParams.action.views
                .filter(([vid, vtype]) => vtype !== "search")
                .map(([vid, vtype]) => {
                    const view = this.props.viewSwitcherEntries.find((v) => v.type === vtype);
                    if (view) {
                        return Object.assign({}, view, { viewID: vid });
                    } else {
                        return {
                            viewID: vid,
                            type: vtype,
                            multiRecord: !this.constructor.multiRecord,
                        };
                    }
                });
            this.viewParams.action = Object.assign({}, this.viewParams.action, {
                controlPanelFieldsView,
                _views: this.viewParams.action.views,
                views,
            });
        }
    }
    Controller.template = legacyViewTemplate;

    Controller.components = { ViewAdapter };
    Controller.display_name = LegacyView.prototype.display_name;
    Controller.icon = LegacyView.prototype.icon;
    Controller.isMobileFriendly = LegacyView.prototype.mobile_friendly;
    Controller.multiRecord = LegacyView.prototype.multi_record;
    Controller.type = LegacyView.prototype.viewType;
    Controller.isLegacy = true;
    if (!viewRegistry.contains(name)) {
        viewRegistry.add(name, Controller);
    }
}

// register views already in the legacy registry, and listens to future registrations
for (const [name, action] of Object.entries(legacyViewRegistry.entries())) {
    registerView(name, action);
}
legacyViewRegistry.onAdd(registerView);
