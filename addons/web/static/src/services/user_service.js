/** @odoo-module **/

import { browser } from "../core/browser";
import { serviceRegistry } from "../webclient/service_registry";
import { SwitchCompanyMenu } from "../webclient/switch_company_menu/switch_company_menu";

export function computeAllowedCompanyIds(cidsFromHash) {
  const { user_companies } = odoo.session_info;

  let allowedCompanies = cidsFromHash || [];
  const allowedCompaniesFromSession = user_companies.allowed_companies;
  const notReallyAllowedCompanies = allowedCompanies.filter(
    (id) => !(id in allowedCompaniesFromSession)
  );

  if (!allowedCompanies.length || notReallyAllowedCompanies.length) {
    allowedCompanies = [user_companies.current_company];
  }
  return allowedCompanies;
}

/**
 * @param {function} getAllowedCompanyIds function that returns the allowed
 *   company ids.
 * @returns {function} function that takes a mode ('toggle' or 'loginto') and
 *   a company id, and that returns the selected company ids following that
 *   operation.
 */
export function makeSetCompanies(getAllowedCompanyIds) {
  return function setCompanies(mode, companyId) {
    let nextCompanyIds = getAllowedCompanyIds().slice();
    if (mode === "toggle") {
      if (nextCompanyIds.includes(companyId)) {
        nextCompanyIds = nextCompanyIds.filter((id) => id !== companyId);
      } else {
        nextCompanyIds.push(companyId);
      }
    } else if (mode === "loginto") {
      if (nextCompanyIds.includes(companyId)) {
        nextCompanyIds = nextCompanyIds.filter((id) => id !== companyId);
      }
      nextCompanyIds.unshift(companyId);
    }
    return nextCompanyIds.length ? nextCompanyIds : [companyId];
  };
}

export const userService = {
  dependencies: ["router", "cookie"],
  deploy(env) {
    const { router, cookie } = env.services;
    const info = odoo.session_info;
    const {
      user_context,
      username,
      name,
      is_system,
      is_admin,
      partner_id,
      user_companies,
      home_action_id,
      show_effect: showEffect,
    } = info;

    let cids;
    if ("cids" in router.current.hash) {
      cids = router.current.hash.cids;
    } else if ("cids" in cookie.current) {
      cids = cookie.current.cids;
    }
    const allowedCompanies = computeAllowedCompanyIds(
      cids && cids.split(",").map((id) => parseInt(id, 10))
    );
    let context = {
      lang: user_context.lang,
      tz: user_context.tz,
      uid: info.uid,
      allowed_company_ids: allowedCompanies,
    };

    cids = allowedCompanies.join(",");
    router.replaceState({ "lock cids": cids });
    cookie.setCookie("cids", cids);

    odoo.systrayRegistry.add("SwitchCompanyMenu", SwitchCompanyMenu, { sequence: 1 });

    const setCompanies = makeSetCompanies(() => allowedCompanies);
    return {
      context,
      get userId() {
        return context.uid;
      },
      name,
      userName: username,
      isAdmin: is_admin,
      isSystem: is_system,
      partnerId: partner_id,
      allowed_companies: user_companies.allowed_companies,
      current_company: user_companies.allowed_companies[allowedCompanies[0]],
      get lang() {
        return context.lang;
      },
      get tz() {
        return context.tz;
      },
      home_action_id,
      get db() {
        const res = {
          name: info.db,
        };
        if ("dbuuid" in info) {
          res.uuid = info.dbuuid;
        }
        return res;
      },
      showEffect,
      setCompanies: (mode, companyId) => {
        const nextCompanyIds = setCompanies(mode, companyId).join(",");
        router.pushState({ "lock cids": nextCompanyIds });
        cookie.setCookie("cids", nextCompanyIds);
        browser.setTimeout(() => window.location.reload()); // history.pushState is a little async
      },
    };
  },
};

serviceRegistry.add("user", userService);
