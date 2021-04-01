/** @odoo-module **/

import { formatFloat, humanNumber } from "./numbers";

export function formatCurrency(value, cid, options = {}) {
  if (value === false) {
    return "";
  }
  const currency = odoo.session_info.currencies[cid];
  const { noSymbol } = options || {};
  const digits = (currency && currency.digits) || options.digits;

  const formatted = options.humanReadable
    ? humanNumber(value)
    : formatFloat(value, { precision: digits && digits[1] });
  if (!currency || noSymbol) {
    return formatted;
  }
  if (currency.position === "after") {
    return `${formatted} ${currency.symbol}`;
  } else {
    return `${currency.symbol} ${formatted}`;
  }
}
