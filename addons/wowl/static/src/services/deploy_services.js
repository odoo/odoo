/** @odoo-module **/
import { serviceRegistry } from "../webclient/service_registry";

export async function deployServices(env) {
  const toDeploy = new Set();
  let timeoutId;
  serviceRegistry.on("UPDATE", null, async (payload) => {
    const { operation, value } = payload;
    if (operation === "delete") {
      // We hardly see why it would be usefull to remove a service.
      // Furthermore we could encounter problems with dependencies.
      // Keep it simple!
      return;
    }
    if (toDeploy.size) {
      toDeploy.add(value);
    } else {
      timeoutId = await _deployServices(env, toDeploy, timeoutId);
    }
  });
  timeoutId = await _deployServices(env, toDeploy, timeoutId);
}

async function _deployServices(env, toDeploy, timeoutId) {
  const services = env.services;
  odoo.serviceRegistry;
  for (const service of odoo.serviceRegistry.getAll()) {
    if (!(service.name in services)) {
      toDeploy.add(service);
    }
  }

  // deploy as many services in parallel as possible
  function deploy() {
    let service = null;
    const proms = [];
    while ((service = findNext())) {
      let name = service.name;
      toDeploy.delete(service);
      const serviceEnv = Object.create(env);
      serviceEnv.services = {};
      if (service.dependencies) {
        for (let dep of service.dependencies) {
          serviceEnv.services[dep] = env.services[dep];
        }
      }
      const value = service.deploy(serviceEnv);
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
