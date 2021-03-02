/** @odoo-module **/

import { serviceRegistry } from "../webclient/service_registry";

export const titleService = {
  name: "title",
  deploy() {
    const titleParts = {};

    function getParts() {
      return Object.assign({}, titleParts);
    }

    function setParts(parts) {
      for (const key in parts) {
        const val = parts[key];
        if (!val) {
          delete titleParts[key];
        } else {
          titleParts[key] = val;
        }
      }
      document.title = Object.values(titleParts).join(" - ");
    }

    return {
      /**
       * @returns {string}
       */
      get current() {
        return document.title;
      },
      getParts,
      setParts,
    };
  },
};

serviceRegistry.add("title", titleService);