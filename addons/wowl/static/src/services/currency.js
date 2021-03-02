/** @odoo-module **/

import { serviceRegistry } from "./service_registry";

export const currencyService = {
  name: "currency",
  dependencies: ["localization"],
  deploy: async (env) => {
    const { currencies } = odoo.session_info;
    const { localization: l10n } = env.services;
    const getAll = () => Object.values(currencies);
    const get = (cid) => {
      if (typeof cid === "number") {
        return currencies[cid];
      }
      return getAll().find((c) => c.name === cid);
    };
    const format = (value, cid, options = {}) => {
      if (value === false) {
        return "";
      }
      const currency = get(cid);
      const { noSymbol } = options || {};
      const digits = (currency && currency.digits) || options.digits;
      const formatted = options.humanReadable
        ? l10n.humanNumber(value)
        : l10n.formatFloat(value, { precision: digits && digits[1] });
      if (!currency || noSymbol) {
        return formatted;
      }
      if (currency.position === "after") {
        return `${formatted} ${currency.symbol}`;
      } else {
        return `${currency.symbol} ${formatted}`;
      }
    };
    return { get, getAll, format };
  },
};

serviceRegistry.add("currency", currencyService)