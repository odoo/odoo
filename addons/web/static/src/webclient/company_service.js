/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { session } from "@web/session";
import { UPDATE_METHODS } from "@web/core/orm_service";
import { cookie } from "@web/core/browser/cookie";

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

function computeActiveCompanyIds(cids) {
    const { user_companies } = session;
    let activeCompanyIds = cids || [];
    const availableCompaniesFromSession = user_companies.allowed_companies;
    const notAllowedCompanies = activeCompanyIds.filter(
        (id) => !(id in availableCompaniesFromSession)
    );

    if (!activeCompanyIds.length || notAllowedCompanies.length) {
        activeCompanyIds = [user_companies.current_company];
    }
    return activeCompanyIds;
}

function getCompanyIdsFromBrowser(hash) {
    let cids;
    if ("cids" in hash) {
        // backward compatibility s.t. old urls (still using "," as separator) keep working
        // deprecated as of 17.0
        let separator = CIDS_HASH_SEPARATOR;
        if (typeof hash.cids === "string" && !hash.cids.includes(CIDS_HASH_SEPARATOR)) {
            separator = ",";
        }
        cids = parseCompanyIds(hash.cids, separator);
    } else if (cookie.get("cids")) {
        cids = parseCompanyIds(cookie.get("cids"));
    }
    return cids || [];
}

export const companyService = {
    dependencies: ["user", "router", "action", "orm", "field"],
    async: ["setCompanies"],
    start(env, { user, router, action, orm, field }) {
        const allowedCompanies = session.user_companies.allowed_companies;
        const disallowedAncestorCompanies = session.user_companies.disallowed_ancestor_companies;
        const allowedCompaniesWithAncestors = {
            ...allowedCompanies,
            ...disallowedAncestorCompanies,
        };
        const activeCompanyIds = computeActiveCompanyIds(
            getCompanyIdsFromBrowser(router.current.hash)
        );

        // update browser data
        const cidsHash = formatCompanyIds(activeCompanyIds, CIDS_HASH_SEPARATOR);
        router.replaceState({ cids: cidsHash }, { lock: true });
        cookie.set("cids", formatCompanyIds(activeCompanyIds));
        user.updateContext({ allowed_company_ids: activeCompanyIds });

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
            allowedCompanies,
            allowedCompaniesWithAncestors,
            disallowedAncestorCompanies,

            get activeCompanyIds() {
                return activeCompanyIds.slice();
            },

            get currentCompany() {
                return allowedCompanies[activeCompanyIds[0]];
            },

            getCompany(companyId) {
                return allowedCompaniesWithAncestors[companyId];
            },

            /**
             * @param {Array<>} companyIds - List of companies to log into
             * @param {boolean} [includeChildCompanies=true] - If true, will also
             * log into each child of each companyIds (default is true)
             */
            async setCompanies(companyIds, includeChildCompanies = true) {
                const newCompanyIds = companyIds.length ? companyIds : [activeCompanyIds[0]];

                const currentModel = router.current.hash.model;
                const currentId = router.current.hash.id;
                const currentMenu = router.current.hash.menu_id;

                function addCompanies(companyIds) {
                    for (const companyId of companyIds) {
                        if (!newCompanyIds.includes(companyId)) {
                            newCompanyIds.push(companyId);
                            addCompanies(allowedCompanies[companyId].child_ids);
                        }
                    }
                }

                let stayOnCurrentPage = true;

                if (currentModel && currentId && 'company_id' in await field.loadFields(currentModel)) {
                    try {
                        await orm.call(
                            currentModel,
                            "check_access_rule",
                            [currentId, "read"],
                            { context: { allowed_company_ids: newCompanyIds } },
                        );
                    } catch {
                        stayOnCurrentPage = false;
                    }
                }

                if (includeChildCompanies) {
                    addCompanies(
                        companyIds.flatMap((companyId) => allowedCompanies[companyId].child_ids)
                    );
                }

                const cidsHash = formatCompanyIds(newCompanyIds, CIDS_HASH_SEPARATOR);
                
                if (stayOnCurrentPage) {
                    router.pushState({ cids: cidsHash }, { lock: true });
                }
                else {
                    router.pushState({ cids: cidsHash, menu_id: currentMenu }, { replace: true });
                }
                cookie.set("cids", formatCompanyIds(newCompanyIds));
                browser.setTimeout(() => browser.location.reload()); // history.pushState is a little async
            },
        };
    },
};

registry.category("services").add("company", companyService);
