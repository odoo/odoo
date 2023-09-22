/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { session } from "@web/session";
import { UPDATE_METHODS } from "@web/core/orm_service";

const CIDS_HASH_SEPARATOR = "-";

function parseCompanyIds(cids, separator = ",") {
    if (typeof cids === "string") {
        return cids.split(separator).map(Number);
    } else if (typeof cids === "number") {
        return [cids];
    }
    return [];
}

function formatCompanyIds(cids, separator = ",") {
    return cids.join(separator);
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
        const hash = router.current.hash;
        if ("cids" in hash) {
            // backward compatibility s.t. old urls (still using "," as separator) keep working
            // deprecated as of 17.0
            let separator = CIDS_HASH_SEPARATOR;
            if (typeof hash.cids === "string" && !hash.cids.includes(CIDS_HASH_SEPARATOR)) {
                separator = ",";
            }
            cids = parseCompanyIds(hash.cids, separator);
        } else if ("cids" in cookie.current) {
            cids = parseCompanyIds(cookie.current.cids);
        }

        const availableCompanies = session.user_companies.allowed_companies;
        const allowedCompanyIds = computeAllowedCompanyIds(cids);
        const nextAvailableCompanies = allowedCompanyIds.slice(); // not using a Set because order is important
        nextAvailableCompanies.add = (companyId) => {
            if (!nextAvailableCompanies.includes(companyId)) {
                nextAvailableCompanies.push(companyId);
                availableCompanies[companyId].child_ids.map(nextAvailableCompanies.add);
            }
        };
        nextAvailableCompanies.remove = (companyId) => {
            if (nextAvailableCompanies.includes(companyId)) {
                nextAvailableCompanies.splice(nextAvailableCompanies.indexOf(companyId), 1);
                availableCompanies[companyId].child_ids.map(nextAvailableCompanies.remove);
            }
        };

        const cidsHash = formatCompanyIds(allowedCompanyIds, CIDS_HASH_SEPARATOR);
        router.replaceState({ cids: cidsHash }, { lock: true });
        cookie.setCookie("cids", formatCompanyIds(allowedCompanyIds));
        user.updateContext({ allowed_company_ids: allowedCompanyIds });

        // reload the page if changes are being done to `res.company`
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
            nextAvailableCompanies,
            get allowedCompanyIds() {
                return allowedCompanyIds.slice();
            },
            get currentCompany() {
                return availableCompanies[allowedCompanyIds[0]];
            },
            getCompany(companyId) {
                return availableCompanies[companyId];
            },
            setCompanies(mode, companyId) {
                if (mode === "toggle") {
                    if (nextAvailableCompanies.includes(companyId)) {
                        nextAvailableCompanies.remove(companyId);
                    } else {
                        nextAvailableCompanies.add(companyId);
                    }
                } else if (mode === "loginto") {
                    nextAvailableCompanies.splice(0, nextAvailableCompanies.length);
                    nextAvailableCompanies.add(companyId);
                }
            },
            logNextCompanies() {
                const next = nextAvailableCompanies.length
                    ? nextAvailableCompanies
                    : [allowedCompanyIds[0]];
                router.pushState(
                    { cids: formatCompanyIds(next, CIDS_HASH_SEPARATOR) },
                    { lock: true }
                );
                cookie.setCookie("cids", formatCompanyIds(next));
                browser.setTimeout(() => browser.location.reload()); // history.pushState is a little async
            },
        };
    },
};

registry.category("services").add("company", companyService);
