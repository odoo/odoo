/** @odoo-module **/

import { useService } from "../core/hooks";
import { serviceRegistry } from "../webclient/service_registry";

/**
 * This ORM service is the standard way to interact with the ORM in python from
 * the javascript codebase.
 */

// -----------------------------------------------------------------------------
// Helper
// -----------------------------------------------------------------------------
function assignOptions(kwargs, options, whileList) {
  for (let elem of whileList) {
    if (elem in options) {
      kwargs[elem] = options[elem];
    }
  }
}

// -----------------------------------------------------------------------------
// ORM
// -----------------------------------------------------------------------------

class ORM {
  constructor(rpc, user) {
    this.rpc = rpc;
    this.user = user;
  }

  call(model, method, args = [], kwargs = {}) {
    let url = `/web/dataset/call_kw/${model}/${method}`;
    const fullContext = Object.assign({}, this.user.context, kwargs.context || {});
    const fullKwargs = Object.assign({}, kwargs, { context: fullContext });
    let params = {
      model,
      method,
      args,
      kwargs: fullKwargs,
    };
    return this.rpc(url, params);
  }

  create(model, state, ctx) {
    return this.call(model, "create", [state], { context: ctx });
  }

  read(model, ids, fields, ctx) {
    return this.call(model, "read", [ids, fields], { context: ctx });
  }

  unlink(model, ids, ctx) {
    return this.call(model, "unlink", [ids], { context: ctx });
  }

  write(model, ids, data, ctx) {
    return this.call(model, "write", [ids, data], { context: ctx });
  }

  search(model, domain, options = {}, ctx = {}) {
    const kwargs = {
      context: ctx,
    };
    assignOptions(kwargs, options, ["offset", "limit", "order"]);
    return this.call(model, "search", [domain], kwargs);
  }

  readGroup(model, domain, fields, groupby, options = {}, ctx = {}) {
    const kwargs = {
      domain,
      groupby,
      fields,
      context: ctx,
    };
    assignOptions(kwargs, options, ["lazy", "offset", "orderby", "limit"]);
    return this.call(model, "web_read_group", [], kwargs);
  }

  searchRead(model, domain, fields, options = {}, ctx = {}) {
    const kwargs = { context: ctx, domain, fields };
    assignOptions(kwargs, options, ["offset", "limit", "order"]);
    return this.call(model, "search_read", [], kwargs);
  }

  webSearchRead(model, domain, fields, options = {}, ctx = {}) {
    const kwargs = { context: ctx, domain, fields };
    assignOptions(kwargs, options, ["offset", "limit", "order"]);
    return this.call(model, "web_search_read", [], kwargs);
  }
}

/**
 * Note:
 *
 * when we will need a way to configure a rpc (for example, to setup a "shadow"
 * flag, or some way of not displaying errors), we can use the following api:
 *
 * this.orm = useService('orm');
 *
 * ...
 *
 * const result = await this.orm.withOption({shadow: true}).read('res.partner', [id]);
 */
export const ormService = {
  dependencies: ["rpc", "user"],
  deploy(env) {
    const { rpc, user } = env.services;
    return new ORM(rpc, user);
  },
  specializeForComponent() {
    const rpc = useService("rpc");
    const user = useService("user");
    return new ORM(rpc, user);
  },
};

serviceRegistry.add("orm", ormService);
