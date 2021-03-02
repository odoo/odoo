/** @odoo-module **/

import { useService } from "../core/hooks";
import { ViewNotFoundError } from "../actions/action_service";
import { useDebugManager } from "../debug_manager/debug_manager";
import { Dialog } from "../components/dialog/dialog";
import { objectToQuery } from "../services/router";
import { ComponentAdapter } from "web.OwlCompatibility";
import { mapDoActionOptionAPI } from "./utils";
import { setupDebugAction, setupDebugViewForm, setupDebugView } from "./debug_manager";

const { Component, hooks, tags } = owl;

const reBSTooltip = /^bs-.*$/;

function cleanDomFromBootstrap() {
  const body = document.body;
  // multiple bodies in tests
  // Bootstrap tooltips
  const tooltips = body.querySelectorAll("body .tooltip");
  for (const tt of tooltips) {
    if (Array.from(tt.classList).find((cls) => reBSTooltip.test(cls))) {
      tt.parentNode.removeChild(tt);
    }
  }
}

class ActionAdapter extends ComponentAdapter {
  constructor(...args) {
    super(...args);
    this.actionService = useService("action");
    this.router = useService("router");
    this.title = useService("title");
    this.notifications = useService("notification");
    this.dialogs = useService("dialog");
    this.wowlEnv = this.env;
    // a legacy widget widget can push_state anytime including during its async rendering
    // In Wowl, we want to have all states pushed during the same setTimeout.
    // This is protected in legacy (backward compatibility) but should not e supported in Wowl
    this.tempQuery = {};
    let originalUpdateControlPanel;
    hooks.onMounted(async () => {
      this.title.setParts({ action: this.widget.getTitle() });
      const query = objectToQuery(this.widget.getState());
      Object.assign(query, this.tempQuery);
      this.tempQuery = null;
      this.__widget = this.widget;
      this.router.pushState(query);
      this.wowlEnv.bus.on("ACTION_MANAGER:UPDATE", this, (info) => {
        if (info.type === "MAIN") {
          this.env.bus.trigger("close_dialogs");
        }
        cleanDomFromBootstrap();
      });
      originalUpdateControlPanel = this.__widget.updateControlPanel.bind(this.__widget);
      this.__widget.updateControlPanel = (newProps) => {
        this.trigger("controller-title-updated", this.__widget.getTitle());
        return originalUpdateControlPanel(newProps);
      };
      await Promise.resolve(); // see https://github.com/odoo/owl/issues/809
      this.trigger("controller-title-updated", this.__widget.getTitle());
    });
    hooks.onWillUnmount(() => {
      this.__widget.updateControlPanel = originalUpdateControlPanel;
      this.wowlEnv.bus.off("ACTION_MANAGER:UPDATE", this);
    });
  }

  _trigger_up(ev) {
    const payload = ev.data;
    if (ev.name === "do_action") {
      const actionContext = payload.action.context;
      // The context needs to be evaluated if it comes from the legacy compound context class.
      if (
        typeof actionContext == "object" &&
        actionContext.__ref &&
        actionContext.__ref === "compound_context"
      ) {
        payload.action.context = actionContext.eval();
      }
      this.onReverseBreadcrumb = ev.data.options && ev.data.options.on_reverse_breadcrumb;
      const legacyOptions = mapDoActionOptionAPI(ev.data.options);
      this.actionService.doAction(payload.action, legacyOptions);
    } else if (ev.name === "breadcrumb_clicked") {
      this.actionService.restore(payload.controllerID);
    } else if (ev.name === "push_state") {
      const query = objectToQuery(payload.state);
      if (this.tempQuery) {
        Object.assign(this.tempQuery, query);
        return;
      }
      this.router.pushState(query);
    } else if (ev.name === "warning") {
      if (payload.type === "dialog") {
        class WarningDialog extends Component {}
        WarningDialog.template = tags.xml`
            <Dialog title="props.title">
              <t t-esc="props.message"/>
            </Dialog>
            `;
        WarningDialog.components = { Dialog };
        this.dialogs.open(WarningDialog, { title: payload.title, message: payload.message });
      } else {
        this.notifications.create(payload.message, {
          className: payload.className,
          icon: payload.icon,
          sticky: payload.sticky,
          title: payload.title,
          type: "warning",
        });
      }
    } else {
      super._trigger_up(ev);
    }
  }

  /**
   * This function is called just before the component will be unmounted,
   * because it will be replaced by another one. However, we need to keep it
   * alive, because we might come back to this one later. We thus return the
   * widget instance, and set this.widget to null so that it is not destroyed
   * by the compatibility layer. That instance will be destroyed by the
   * ActionManager service when it will be removed from the controller stack,
   * and if we ever come back to that controller, the instance will be given
   * in props so that we can re-use it.
   */
  exportState() {
    this.widget = null;
    return {
      __legacy_widget__: this.__widget,
      __on_reverse_breadcrumb__: this.onReverseBreadcrumb,
    };
  }

  canBeRemoved() {
    return this.__widget.canBeRemoved();
  }
}

export class ClientActionAdapter extends ActionAdapter {
  constructor(parent, props) {
    super(parent, props);
    useDebugManager((accessRights) =>
      setupDebugAction(accessRights, this.wowlEnv, this.props.widgetArgs[0])
    );
    this.env = Component.env;
  }

  async willStart() {
    if (this.props.widget) {
      this.widget = this.props.widget;
      this.widget.setParent(this);
      if (this.props.onReverseBreadcrumb) {
        await this.props.onReverseBreadcrumb();
      }
      return this.updateWidget();
    }
    return super.willStart();
  }

  /**
   * @override
   */
  updateWidget() {
    return this.widget.do_show();
  }

  do_push_state() {}
}

const magicReloadSymbol = Symbol("magicReload");

function useMagicLegacyReload() {
  const comp = Component.current;
  if (comp.props.widget && comp.props.widget[magicReloadSymbol]) {
    return comp.props.widget[magicReloadSymbol];
  }
  let legacyReloadProm = null;
  const getReloadProm = () => legacyReloadProm;
  let manualReload;
  hooks.onMounted(() => {
    const widget = comp.widget;
    const controllerReload = widget.reload;
    widget.reload = function (...args) {
      manualReload = true;
      legacyReloadProm = controllerReload.call(widget, ...args);
      return legacyReloadProm.then(() => {
        if (manualReload) {
          legacyReloadProm = null;
          manualReload = false;
        }
      });
    };
    const controllerUpdate = widget.update;
    widget.update = function (...args) {
      const updateProm = controllerUpdate.call(widget, ...args);
      const manualUpdate = !manualReload;
      if (manualUpdate) {
        legacyReloadProm = updateProm;
      }
      return updateProm.then(() => {
        if (manualUpdate) {
          legacyReloadProm = null;
        }
      });
    };
    widget[magicReloadSymbol] = getReloadProm;
  });
  return getReloadProm;
}

export class ViewAdapter extends ActionAdapter {
  constructor(...args) {
    super(...args);
    this.model = useService("model");
    this.actionService = useService("action");
    this.vm = useService("view");
    this.shouldUpdateWidget = true;
    this.magicReload = useMagicLegacyReload();
    const envWowl = this.env;
    useDebugManager((accessRights) =>
      setupDebugAction(accessRights, envWowl, this.props.viewParams.action)
    );
    useDebugManager((accessRights) =>
      setupDebugView(accessRights, envWowl, this, this.props.viewParams.action)
    );
    if (this.props.viewInfo.type === "form") {
      useDebugManager(() => setupDebugViewForm(envWowl, this, this.props.viewParams.action));
    }
    if (!envWowl.inDialog) {
      hooks.onMounted(() => {
        envWowl.bus.on("ACTION_MANAGER:UPDATE", this, (info) => {
          switch (info.type) {
            case "OPEN_DIALOG": {
              // we are a main action, and a dialog is going to open:
              // we should not reload
              this.shouldUpdateWidget = false;
              break;
            }
            case "CLOSE_DIALOG": {
              this.shouldUpdateWidget = false;
              info.closingProms.push(() => this.magicReload());
              break;
            }
          }
        });
      });
    }
    this.env = Component.env;
  }

  async willStart() {
    if (this.props.widget) {
      this.widget = this.props.widget;
      this.widget.setParent(this);
      if (this.props.onReverseBreadcrumb) {
        await this.props.onReverseBreadcrumb();
      }
      return this.updateWidget(this.props.viewParams);
    } else {
      const view = new this.props.View(this.props.viewInfo, this.props.viewParams);
      this.widget = await view.getController(this);
      if (this.__owl__.status === 5 /* DESTROYED */) {
        // the component might have been destroyed meanwhile, but if so, `this.widget` wasn't
        // destroyed by OwlCompatibility layer as it wasn't set yet, so destroy it now
        this.widget.destroy();
        return Promise.resolve();
      }
      return this.widget._widgetRenderAndInsert(() => {});
    }
  }

  /**
   * @override
   */
  async updateWidget() {
    const shouldUpdateWidget = this.shouldUpdateWidget;
    this.shouldUpdateWidget = true;
    if (!shouldUpdateWidget) {
      return this.magicReload();
    }
    await this.widget.willRestore();
    const options = Object.assign({}, this.props.viewParams, {
      shouldUpdateSearchComponents: true,
    });
    if (!this.magicReload()) {
      this.widget.reload(options);
    }
    return this.magicReload();
  }

  /**
   * Override to add the state of the legacy controller in the exported state.
   */
  exportState() {
    const widgetState = this.widget.exportState();
    const state = super.exportState();
    return Object.assign({}, state, widgetState);
  }

  async loadViews(model, context, views) {
    return (await this.vm.loadViews({ model, views, context }, {})).fields_views;
  }

  /**
   * @private
   * @param {OdooEvent} ev
   */
  async _trigger_up(ev) {
    const payload = ev.data;
    if (ev.name === "switch_view") {
      const state = ev.target.exportState();
      try {
        await this.actionService.switchView(payload.view_type, {
          recordId: payload.res_id,
          recordIds: state.resIds,
          searchModel: state.searchModel,
          searchPanel: state.searchPanel,
        });
      } catch (e) {
        if (e instanceof ViewNotFoundError) {
          return;
        }
        throw e;
      }
    } else if (ev.name === "execute_action") {
      const onSuccess = payload.on_success || (() => {});
      const onFail = payload.on_fail || (() => {});
      this.actionService
        .doActionButton({
          args: payload.action_data.args,
          buttonContext: payload.action_data.context,
          context: payload.env.context,
          close: payload.action_data.close,
          model: payload.env.model,
          name: payload.action_data.name,
          recordId: payload.env.currentID || null,
          recordIds: payload.env.resIDs,
          special: payload.action_data.special,
          type: payload.action_data.type,
          onClose: payload.on_closed,
          effect: payload.action_data.effect,
        })
        .then(onSuccess)
        .catch(onFail);
    } else {
      super._trigger_up(ev);
    }
  }
}
