/** @odoo-module **/

import { browser } from "../../core/browser";
import { userMenuRegistry } from "../user_menu_registry";

const { Component } = owl;

function documentationItem(env) {
  const documentationURL = "https://www.odoo.com/documentation/user";
  return {
    type: "item",
    description: env._t("Documentation"),
    href: documentationURL,
    callback: () => {
      browser.open(documentationURL, "_blank");
    },
    sequence: 10,
  };
}

function supportItem(env) {
  const buyEnterpriseURL = "https://www.odoo.com/buy";
  return {
    type: "item",
    description: env._t("Support"),
    href: buyEnterpriseURL,
    callback: () => {
      browser.open(buyEnterpriseURL, "_blank");
    },
    sequence: 20,
  };
}

class ShortCutsDialog extends Component {}
ShortCutsDialog.template = "web.UserMenu.ShortCutsDialog";

function shortCutsItem(env) {
  return {
    type: "item",
    description: env._t("Shortcuts"),
    callback: () => {
      const title = env._t("Shortcuts");
      env.services.dialog.open(ShortCutsDialog, { title });
    },
    sequence: 30,
  };
}

function separator(env) {
  return {
    type: "separator",
    sequence: 40,
  };
}

function preferencesItem(env) {
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

function odooAccountItem(env) {
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
    sequence: 60,
  };
}

function logOutItem(env) {
  const route = "/web/session/logout";
  return {
    type: "item",
    description: env._t("Log out"),
    href: `${browser.location.origin}${route}`,
    callback: () => {
      browser.location.href = route;
    },
    sequence: 70,
  };
}

userMenuRegistry
  .add("documentation", documentationItem)
  .add("support", supportItem)
  .add("shortcuts", shortCutsItem)
  .add("separator", separator)
  .add("profile", preferencesItem)
  .add("odoo_account", odooAccountItem)
  .add("log_out", logOutItem);
