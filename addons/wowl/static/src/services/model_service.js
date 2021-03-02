/** @odoo-module **/

import { serviceRegistry } from "../webclient/service_registry";

const { Component } = owl;

function read(rpc, env, model) {
  return (ids, fields, ctx) => callModel(rpc, env, model)("read", [ids, fields], { context: ctx });
}

function create(rpc, env, model) {
  return (state, ctx) => callModel(rpc, env, model)("create", [state], { context: ctx });
}

function unlink(rpc, env, model) {
  return (ids, ctx) => callModel(rpc, env, model)("unlink", [ids], { context: ctx });
}

function write(rpc, env, model) {
  return (ids, data, ctx) => callModel(rpc, env, model)("write", [ids, data], { context: ctx });
}

function readGroup(rpc, env, model) {
  return (domain, fields, groupby, options = {}, ctx = {}) => {
    const kwargs = {
      domain,
      groupby,
      fields,
      context: ctx,
    };
    if (options.lazy) {
      kwargs.lazy = options.lazy;
    }
    if (options.offset) {
      kwargs.offset = options.offset;
    }
    if (options.orderby) {
      kwargs.orderby = options.orderby;
    }
    if (options.limit) {
      kwargs.limit = options.limit;
    }
    return callModel(rpc, env, model)("web_read_group", [], kwargs);
  };
}

function search(rpc, env, model) {
  return (domain, options = {}, ctx = {}) => {
    const kwargs = {
      context: ctx,
    };
    if (options.offset) {
      kwargs.offset = options.offset;
    }
    if (options.limit) {
      kwargs.limit = options.limit;
    }
    if (options.order) {
      kwargs.order = options.order;
    }
    return callModel(rpc, env, model)("search", [domain], kwargs);
  };
}

function makeSearchRead(method) {
  return function (rpc, env, model) {
    return (domain, fields, options = {}, ctx = {}) => {
      const kwargs = {
        context: ctx,
        domain,
        fields,
      };
      if (options.offset) {
        kwargs.offset = options.offset;
      }
      if (options.limit) {
        kwargs.limit = options.limit;
      }
      if (options.order) {
        kwargs.order = options.order;
      }
      return callModel(rpc, env, model)(method, [], kwargs);
    };
  };
}

function callModel(rpc, env, model) {
  const user = env.services.user;
  return (method, args = [], kwargs = {}) => {
    let url = `/web/dataset/call_kw/${model}/${method}`;
    const fullContext = Object.assign({}, user.context, kwargs.context || {});
    const fullKwargs = Object.assign({}, kwargs, { context: fullContext });
    let params = {
      model,
      method,
    };
    params.args = args;
    params.kwargs = fullKwargs;
    return rpc(url, params);
  };
}

/**
 * Note:
 *
 * when we will need a way to configure a rpc (for example, to setup a "shadow"
 * flag, or some way of not displaying errors), we can use the following api:
 *
 * this.model = useService('model);
 *
 * ...
 *
 * const result = await this.model('res.partner').configure({shadow: true}).read([id]);
 */
export const modelService = {
  name: "model",
  dependencies: ["rpc", "user"],
  deploy(env) {
    return function (model) {
      const rpc = this instanceof Component ? env.services.rpc.bind(this) : env.services.rpc;
      const searchRead = makeSearchRead("search_read");
      const webSearchRead = makeSearchRead("web_search_read");
      return {
        get read() {
          return read(rpc, env, model);
        },
        get unlink() {
          return unlink(rpc, env, model);
        },
        get search() {
          return search(rpc, env, model);
        },
        get searchRead() {
          return searchRead(rpc, env, model);
        },
        get webSearchRead() {
          return webSearchRead(rpc, env, model);
        },
        get create() {
          return create(rpc, env, model);
        },
        get write() {
          return write(rpc, env, model);
        },
        get readGroup() {
          return readGroup(rpc, env, model);
        },
        get call() {
          return callModel(rpc, env, model);
        },
      };
    };
  },
};

serviceRegistry.add("model", modelService);