/** @odoo-module **/

import { serviceRegistry } from "../webclient/service_registry";

export const httpService = {
  deploy() {
    return {
      async get(route, readMethod = "json") {
        const response = await fetch(route, { method: "GET" });
        return response[readMethod]();
      },
      async post(route, params = {}, readMethod = "json") {
        const formData = new FormData();
        for (const key in params) {
          const value = params[key];
          if (Array.isArray(value) && value.length) {
            for (const val of value) {
              formData.append(key, val);
            }
          } else {
            formData.append(key, value);
          }
        }
        const info = {
          body: formData,
          method: "POST",
        };
        const response = await fetch(route, info);
        return response[readMethod]();
      },
    };
  },
};

serviceRegistry.add("http", httpService);
