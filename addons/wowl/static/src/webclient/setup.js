/** @odoo-module **/

const { loadFile } = owl.utils;

export const SPECIAL_METHOD = Symbol("special_method");

/**
 * Deploy all services registered in the service registry, while making sure
 * each service dependencies are properly fulfilled.
 *
 * @param {OdooEnv} env
 * @returns {Promise<void>}
 */
export async function deployServices(env) {
  const toDeploy = new Set();
  let timeoutId;
  odoo.serviceRegistry.on("UPDATE", null, async (payload) => {
    const { operation, key: name, value: service } = payload;
    if (operation === "delete") {
      // We hardly see why it would be usefull to remove a service.
      // Furthermore we could encounter problems with dependencies.
      // Keep it simple!
      return;
    }
    if (toDeploy.size) {
      const namedService = Object.assign(Object.create(service), { name });
      toDeploy.add(namedService);
    } else {
      timeoutId = await _deployServices(env, toDeploy, timeoutId);
    }
  });
  timeoutId = await _deployServices(env, toDeploy, timeoutId);
}

async function _deployServices(env, toDeploy, timeoutId) {
  const services = env.services;
  for (const [name, service] of odoo.serviceRegistry.getEntries()) {
    if (!(name in services)) {
      const namedService = Object.assign(Object.create(service), { name });
      toDeploy.add(namedService);
    }
  }

  // deploy as many services in parallel as possible
  function deploy() {
    let service = null;
    const proms = [];
    while ((service = findNext())) {
      let name = service.name;
      toDeploy.delete(service);
      const value = service.deploy(env);
      if (value && "specializeForComponent" in service) {
        value[SPECIAL_METHOD] = service.specializeForComponent;
      }
      if (value instanceof Promise) {
        proms.push(
          value.then((val) => {
            services[name] = val || null;
            return deploy();
          })
        );
      } else {
        services[service.name] = value || null;
      }
    }
    return Promise.all(proms);
  }
  await deploy();
  clearTimeout(timeoutId);
  timeoutId = undefined;
  if (toDeploy.size) {
    const names = [...toDeploy].map((s) => s.name);
    timeoutId = setTimeout(() => {
      timeoutId = undefined;
      throw new Error(`Some services could not be deployed: ${names}`);
    }, 15000);
    toDeploy.clear();
  }
  return timeoutId;
  function findNext() {
    for (let s of toDeploy) {
      if (s.dependencies) {
        if (s.dependencies.every((d) => d in services)) {
          return s;
        }
      } else {
        return s;
      }
    }
    return null;
  }
}

/**
 * Load all templates from the Odoo server and returns the string. This method
 * does NOT register the templates into Owl.
 *
 * @returns {Promise<string>}
 */
export async function loadTemplates() {
  const templatesUrl = `/wowl/templates/${odoo.session_info.qweb}`;
  const templates = await loadFile(templatesUrl);
  // as we currently have two qweb engines (owl and legacy), owl templates are
  // flagged with attribute `owl="1"`. The following lines removes the 'owl'
  // attribute from the templates, so that it doesn't appear in the DOM. For now,
  // we make the assumption that 'templates' only contains owl templates. We
  // might need at some point to handle the case where we have both owl and
  // legacy templates. At the end, we'll get rid of all this.
  const doc = new DOMParser().parseFromString(templates, "text/xml");
  for (let child of doc.querySelectorAll("templates > [owl]")) {
    child.removeAttribute("owl");
  }
  return new XMLSerializer().serializeToString(doc);
}
