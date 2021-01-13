/** @odoo-module **/
const { utils } = owl;
import { sprintf } from "../utils/strings";
const { escape } = utils;
export const displayNotificationAction = (env, action) => {
  const params = action.params || {};
  const options = {
    className: params.className || "",
    icon: params.icon || "",
    sticky: params.sticky || false,
    title: params.title ? escape(params.title) : "",
    type: params.type || "info",
  };
  let links = (params.links || []).map((link) => {
    return `<a href="${escape(link.url)}" target="_blank">${escape(link.label)}</a>`;
  });
  const message = sprintf(escape(params.message), ...links);
  env.services.notifications.create(message, options);
  return params.next;
};
