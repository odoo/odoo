/** @odoo-module **/

import { browser } from "../../core/browser";

const { Component } = owl;

export function documentationItem(env) {
  const documentationURL = "https://www.odoo.com/documentation/user";
  return {
    type: "item",
    description: env._t("Documentation"),
    href: documentationURL,
    callback: () => {
      browser.open(documentationURL, "_blank");
    },
  };
}

export function supportItem(env) {
  const buyEnterpriseURL = "https://www.odoo.com/buy";
  return {
    type: "item",
    description: env._t("Support"),
    href: buyEnterpriseURL,
    callback: () => {
      browser.open(buyEnterpriseURL, "_blank");
    },
  };
}

class ShortCutsDialog extends Component {}
ShortCutsDialog.template = "web.UserMenu.ShortCutsDialog";

export function shortCutsItem(env) {
  return {
    type: "item",
    description: env._t("Shortcuts"),
    callback: () => {
      const title = env._t("Shortcuts");
      env.services.dialog.open(ShortCutsDialog, { title });
    },
  };
}

export function separator(env) {
  return {
    type: "separator",
  };
}

export function preferencesItem(env) {
  return {
    type: "item",
    description: env._t("Preferences"),
    callback: async function () {
      const actionDescription = await env.services.orm.call("res.users", "action_get");
      actionDescription.res_id = env.services.user.userId;
      env.services.action.doAction(actionDescription);
    },
  };
}

export function odooAccountItem(env) {
  return {
    type: "item",
    description: env._t("My Odoo.com.account"),
    callback: () => {
      env.services
        .rpc("/web/session/account")
        .then((url) => {
          browser.location.href = url;
        })
        .catch(() => {
          browser.location.href = "https://accounts.odoo.com/account";
        });
    },
  };
}

export function logOutItem(env) {
  const route = "/web/session/logout";
  return {
    type: "item",
    description: env._t("Log out"),
    href: `${browser.location.origin}${route}`,
    callback: () => {
      browser.location.href = route;
    },
  };
}
