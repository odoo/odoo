/** @odoo-module **/
const { Component, hooks, tags } = owl;

import { useService } from "../core/hooks";
import { useSetupAction } from "../actions/action_service";
import { viewRegistry } from "../views/view_registry";
import legacyViewRegistry from "web.view_registry";
import { ViewAdapter } from "./action_adapters";
import Widget from "web.Widget";
import { breadcrumbsToLegacy } from "./utils";

function getJsClassWidget(fieldsInfo) {
  const parsedXML = new DOMParser().parseFromString(fieldsInfo.arch, "text/xml");
  const key = parsedXML.documentElement.getAttribute("js_class");
  return legacyViewRegistry.get(key);
}

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
      this.viewParams = {
        action: this.props.action,
        // legacy views automatically add the last part of the breadcrumbs
        breadcrumbs: breadcrumbsToLegacy(this.props.breadcrumbs),
        modelName: this.props.model,
        currentId: this.props.recordId,
        controllerState: {
          currentId:
            "recordId" in this.props
              ? this.props.recordId
              : this.props.state && this.props.state.currentId,
          resIds: this.props.recordIds || (this.props.state && this.props.state.resIds),
          searchModel: this.props.searchModel || (this.props.state && this.props.state.searchModel),
          searchPanel: this.props.searchPanel || (this.props.state && this.props.state.searchPanel),
        },
      };
      this.widget = this.props.state && this.props.state.__legacy_widget__;
      this.onReverseBreadcrumb = this.props.state && this.props.state.__on_reverse_breadcrumb__;
      const { scrollTo } = useSetupAction({
        beforeLeave: () => this.controllerRef.comp.widget.canBeRemoved(),
        export: () => this.controllerRef.comp.exportState(),
      });
      this.onScrollTo = (ev) => {
        scrollTo({ left: ev.detail.left, top: ev.detail.top });
      };
    }

    async willStart() {
      const params = {
        model: this.props.model,
        views: this.props.views,
        context: this.props.context,
      };
      const options = {
        actionId: this.props.actionId,
        context: this.props.context,
        withActionMenus: this.props.withActionMenus,
        withFilters: this.props.withFilters,
      };
      const result = await this.vm.loadViews(params, options);
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
      this.viewParams.action = Object.assign({}, this.viewParams.action, {
        controlPanelFieldsView,
        _views: this.viewParams.action.views,
        views: this.props.viewSwitcherEntries,
      });
    }
  }

  Controller.template = tags.xml`
    <ViewAdapter Component="Widget" View="View" viewInfo="viewInfo" viewParams="viewParams"
                 widget="widget" onReverseBreadcrumb="onReverseBreadcrumb" t-ref="controller"
                 t-on-scrollTo.stop="onScrollTo"/>
  `;
  Controller.components = { ViewAdapter };
  Controller.display_name = LegacyView.prototype.display_name;
  Controller.icon = LegacyView.prototype.icon;
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
