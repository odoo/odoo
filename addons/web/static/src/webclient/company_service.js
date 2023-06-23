/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { symmetricalDifference } from "../core/utils/arrays";
import { session } from "@web/session";
import { UPDATE_METHODS } from "@web/core/orm_service";

function parseCompanyIds(cidsFromHash) {
    const cids = [];
    if (typeof cidsFromHash === "string") {
        cids.push(...cidsFromHash.split(",").map(Number));
    } else if (typeof cidsFromHash === "number") {
        cids.push(cidsFromHash);
    }
    return cids;
}

function computeAllowedCompanyIds(cids) {
    const { user_companies } = session;
    let allowedCompanyIds = cids || [];
    const availableCompaniesFromSession = user_companies.allowed_companies;
    const notReallyAllowedCompanies = allowedCompanyIds.filter(
        (id) => !(id in availableCompaniesFromSession)
    );

    if (!allowedCompanyIds.length || notReallyAllowedCompanies.length) {
        allowedCompanyIds = [user_companies.current_company];
    }
    return allowedCompanyIds;
}

export const companyService = {
    dependencies: ["user", "router", "cookie", "action"],
    start(env, { user, router, cookie, action }) {
        let cids;
        if ("cids" in router.current.hash) {
            cids = parseCompanyIds(router.current.hash.cids);
        } else if ("cids" in cookie.current) {
            cids = parseCompanyIds(cookie.current.cids);
        }
        const allowedCompanyIds = computeAllowedCompanyIds(cids);

        const stringCIds = allowedCompanyIds.join(",");
        router.replaceState({ cids: stringCIds }, { lock: true });
        cookie.setCookie("cids", stringCIds);

        user.updateContext({ allowed_company_ids: allowedCompanyIds });
        const availableCompanies = session.user_companies.allowed_companies;

        env.bus.addEventListener("RPC:RESPONSE", (ev) => {
            const { data, error } = ev.detail;
            const { model, method } = data.params;
            if (!error && model === "res.company" && UPDATE_METHODS.includes(method)) {
                if (!browser.localStorage.getItem("running_tour")) {
                    action.doAction("reload_context");
                }
            }
        });
        return {
            availableCompanies,
            get allowedCompanyIds() {
                return allowedCompanyIds.slice();
            },
            get currentCompany() {
                return availableCompanies[allowedCompanyIds[0]];
            },
            getCompany(companyId) {
                return availableCompanies[companyId];
            },
            getAllChildren(companyId) {
                return [
                    ...availableCompanies[companyId].child_ids,
                    ...availableCompanies[companyId].child_ids.map((child) => this.getAllChildren(child))
                ].flat()
            },
            getChildrenToToggle(companyId) {
                const children = this.getAllChildren(companyId)
                if ( allowedCompanyIds.includes(companyId) ) {
                    return children.filter((id) => allowedCompanyIds.includes(id))
                } else {
                    return children.filter((id) => !allowedCompanyIds.includes(id))
                }
            },
            setCompanies(mode, ...companyIds) {
                // compute next company ids
                let nextCompanyIds;
                if (mode === "toggle") {
                    nextCompanyIds = symmetricalDifference(allowedCompanyIds, companyIds);
                } else if (mode === "loginto") {
                    const companyId = companyIds[0];
                    const children = this.getAllChildren(companyId);
                    if (allowedCompanyIds.length === 1) {
                        // 1 enabled company: stay in single company mode
                        nextCompanyIds = [companyId, ...children];
                    } else {
                        // multi company mode
                        nextCompanyIds = [
                            companyId,
                            ...children,
                            ...allowedCompanyIds.filter((id) => id !== companyId && !children.includes(id)),
                        ];
                    }
                }
                nextCompanyIds = nextCompanyIds.length ? nextCompanyIds : [companyIds[0]];

                // apply them
                router.pushState({ cids: nextCompanyIds }, { lock: true });
                cookie.setCookie("cids", nextCompanyIds);
                browser.setTimeout(() => browser.location.reload()); // history.pushState is a little async
            },
        };
    },
};

registry.category("services").add("company", companyService);
