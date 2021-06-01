/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";

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
    const { user_companies } = odoo.session_info;
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
    dependencies: ["user", "router", "cookie"],
    start(env, { user, router, cookie }) {
        let cids;
        if ("cids" in router.current.hash) {
            cids = parseCompanyIds(router.current.hash.cids);
        } else if ("cids" in cookie.current) {
            cids = parseCompanyIds(cookie.current.cids);
        }
        let allowedCompanyIds = computeAllowedCompanyIds(cids);

        const stringCIds = allowedCompanyIds.join(",");
        router.replaceState({ cids: stringCIds }, { lock: true });
        cookie.setCookie("cids", stringCIds);

        user.updateContext({ allowed_company_ids: allowedCompanyIds });
        const availableCompanies = odoo.session_info.user_companies.allowed_companies;

        return {
            availableCompanies,
            get allowedCompanyIds() {
                return allowedCompanyIds.slice();
            },
            get currentCompany() {
                return availableCompanies[allowedCompanyIds[0]];
            },
            setCompanies(mode, companyId) {
                // compute next company ids
                let nextCompanyIds = allowedCompanyIds.slice();
                if (mode === "toggle") {
                    if (nextCompanyIds.includes(companyId)) {
                        nextCompanyIds = nextCompanyIds.filter((id) => id !== companyId);
                    } else {
                        nextCompanyIds.push(companyId);
                    }
                } else if (mode === "loginto") {
                    if (nextCompanyIds.length === 1) {
                        // 1 enabled company: stay in single company mode
                        nextCompanyIds = [companyId];
                    } else {
                        // multi company mode
                        if (nextCompanyIds.includes(companyId)) {
                            nextCompanyIds = nextCompanyIds.filter((id) => id !== companyId);
                        }
                        nextCompanyIds.unshift(companyId);
                    }
                }
                allowedCompanyIds = nextCompanyIds.length ? nextCompanyIds : [companyId];

                // apply them
                router.pushState({ cids: allowedCompanyIds }, { lock: true });
                cookie.setCookie("cids", allowedCompanyIds);
                browser.setTimeout(() => browser.location.reload()); // history.pushState is a little async
            },
        };
    },
};

registry.category("services").add("company", companyService);
