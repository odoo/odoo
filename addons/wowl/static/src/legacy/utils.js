/** @odoo-module **/

export function mapDoActionOptionAPI(legacyOptions) {
  legacyOptions = Object.assign(legacyOptions || {});
  // use camelCase instead of snake_case for some keys
  Object.assign(legacyOptions, {
    additionalContext: legacyOptions.additional_context,
    clearBreadcrumbs: legacyOptions.clear_breadcrumbs,
    viewType: legacyOptions.view_type,
    resId: legacyOptions.res_id,
    onClose: legacyOptions.on_close,
  });
  delete legacyOptions.additional_context;
  delete legacyOptions.clear_breadcrumbs;
  delete legacyOptions.view_type;
  delete legacyOptions.res_id;
  delete legacyOptions.on_close;
  return legacyOptions;
}

export function makeLegacyActionManagerService(legacyEnv) {
  // add a service to redirect 'do-action' events triggered on the bus in the
  // legacy env to the action-manager service in the wowl env
  return {
    name: "legacy_action_manager",
    dependencies: ["action"],
    deploy(env) {
      legacyEnv.bus.on("do-action", null, (payload) => {
        const legacyOptions = mapDoActionOptionAPI(payload.options);
        env.services.action.doAction(payload.action, legacyOptions);
      });
    },
  };
}

export function makeLegacyRpcService(legacyEnv) {
  return {
    name: "legacy_rpc",
    deploy(env) {
      legacyEnv.bus.on("rpc_request", null, (rpcId) => {
        env.bus.trigger("RPC:REQUEST", rpcId);
      });
      legacyEnv.bus.on("rpc_response", null, (rpcId) => {
        env.bus.trigger("RPC:RESPONSE", rpcId);
      });
      legacyEnv.bus.on("rpc_response_failed", null, (rpcId) => {
        env.bus.trigger("RPC:RESPONSE", rpcId);
      });
    },
  };
}

export function makeLegacySessionService(legacyEnv, session) {
  return {
    name: "legacy_session",
    dependencies: ["user"],
    deploy(env) {
      // userContext, Object.create is incompatible with legacy new Context
      const userContext = Object.assign({}, env.services.user.context);
      legacyEnv.session.userContext = userContext;
      // usually core.session
      session.user_context = userContext;
    },
  };
}

export function mapLegacyEnvToWowlEnv(legacyEnv, wowlEnv) {
  // rpc
  legacyEnv.session.rpc = (...args) => {
    let rejection;
    const prom = new Promise((resolve, reject) => {
      rejection = () => reject();
      const [route, params, settings] = args;
      wowlEnv.services.rpc(route, params, settings).then(resolve).catch(reject);
    });
    prom.abort = rejection;
    return prom;
  };
  // Storages
  function mapStorage(storage) {
    return Object.assign(Object.create(storage), {
      getItem(key, defaultValue) {
        const val = storage.getItem(key);
        return val ? JSON.parse(val) : defaultValue;
      },
      setItem(key, value) {
        storage.setItem(key, JSON.stringify(value));
      },
    });
  }
  legacyEnv.services.local_storage = mapStorage(odoo.browser.localStorage);
  legacyEnv.services.session_storage = mapStorage(odoo.browser.sessionStorage);
  // map WebClientReady
  wowlEnv.bus.on("WEB_CLIENT_READY", null, () => {
    legacyEnv.bus.trigger("web_client_ready");
  });
}

export function breadcrumbsToLegacy(breadcrumbs) {
  if (!breadcrumbs) {
    return;
  }
  return breadcrumbs.slice().map((bc) => {
    return { title: bc.name, controllerID: bc.jsId };
  });
}
