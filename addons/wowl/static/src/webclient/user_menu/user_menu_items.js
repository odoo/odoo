/** @odoo-module **/

import { Dialog } from "../../components/dialog/dialog";

const { Component } = owl;

export function documentationItem(env) {
  const documentationURL = "https://www.odoo.com/documentation/user";
  return {
    type: "item",
    description: env._t("Documentation"),
    href: documentationURL,
    callback: () => {
      odoo.browser.open(documentationURL, "_blank");
    },
    sequence: 10,
  };
}

export function supportItem(env) {
  const buyEnterpriseURL = "https://www.odoo.com/buy";
  return {
    type: "item",
    description: env._t("Support"),
    href: buyEnterpriseURL,
    callback: () => {
      odoo.browser.open(buyEnterpriseURL, "_blank");
    },
    sequence: 20,
  };
}

class ShortCutsDialog extends Component {}
ShortCutsDialog.template = "wowl.UserMenu.ShortCutsDialog";
ShortCutsDialog.components = { Dialog };

export function shortCutsItem(env) {
  return {
    type: "item",
    description: env._t("Shortcuts"),
    callback: () => {
      const title = env._t("Shortcuts");
      env.services.dialog_manager.open(ShortCutsDialog, { title });
    },
    sequence: 30,
  };
}

export function separator(env) {
  return {
    type: "separator",
    sequence: 40,
  };
}

export function preferencesItem(env) {
  return {
    type: "item",
    description: env._t("Preferences"),
    callback: async function () {
      const actionDescription = await env.services.model("res.users").call("action_get");
      actionDescription.res_id = env.services.user.userId;
      env.services.action.doAction(actionDescription);
    },
    sequence: 50,
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
          odoo.browser.location.href = url;
        })
        .catch(() => {
          odoo.browser.location.href = "https://accounts.odoo.com/account";
        });
    },
    sequence: 60,
  };
}

export function logOutItem(env) {
  const route = "/web/session/logout";
  return {
    type: "item",
    description: env._t("Log out"),
    href: `${odoo.browser.location.origin}${route}`,
    callback: () => {
      odoo.browser.location.href = route;
    },
    sequence: 70,
  };
}
