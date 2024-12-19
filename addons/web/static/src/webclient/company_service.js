import { browser } from "@web/core/browser/browser";
import { rpcBus } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { session } from "@web/session";
import { UPDATE_METHODS } from "@web/core/orm_service";
import { cookie } from "@web/core/browser/cookie";
import { user } from "@web/core/user";
import { router } from "@web/core/browser/router";
import { allowedFns } from "@web/core/py_js/py_interpreter";

const CIDS_SEPARATOR = "-";

function parseCompanyIds(cids, separator = CIDS_SEPARATOR) {
    if (typeof cids === "string") {
        return cids.split(separator).map(Number);
    } else if (typeof cids === "number") {
        return [cids];
    }
    return [];
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

function getCompanyIds() {
    let cids;
    // backward compatibility, in old urls cid was still used.
    // deprecated as of saas-17.3
    const state = router.current;
    if ("cids" in state) {
        // backward compatibility s.t. old urls (still using "," as separator) keep working
        // deprecated as of 17.0
        if (typeof state.cids === "string" && !state.cids.includes(CIDS_SEPARATOR)) {
            cids = parseCompanyIds(state.cids, ",");
        } else {
            cids = parseCompanyIds(state.cids);
        }
    } else if (cookie.get("cids")) {
        cids = parseCompanyIds(cookie.get("cids"));
    }
    return cids || [];
}

export const companyService = {
    dependencies: ["action"],
    start(env, { action }) {
        const allowedCompanies = session.user_companies.allowed_companies;
        const disallowedAncestorCompanies = session.user_companies.disallowed_ancestor_companies;
        const allowedCompaniesWithAncestors = {
            ...allowedCompanies,
            ...disallowedAncestorCompanies,
        };
        const activeCompanyIds = computeActiveCompanyIds(getCompanyIds());

        // update browser data
        cookie.set("cids", activeCompanyIds.join(CIDS_SEPARATOR));
        user.updateContext({ allowed_company_ids: activeCompanyIds });

        // reload the page if changes are being done to `res.company`
        rpcBus.addEventListener("RPC:RESPONSE", (ev) => {
            const { data, error } = ev.detail;
            const { model, method } = data.params;
            if (!error && model === "res.company" && UPDATE_METHODS.includes(method)) {
                if (!browser.localStorage.getItem("running_tour")) {
                    action.doAction("reload_context");
                }
            }
        });

        const evalContext = {
            /**
             * @type {boolean}
             * A boolean indicating whether the user has access to multiple companies.
             */
            multi_company: Object.values(allowedCompanies).length > 1,

            /**
             * @type {Array.<number>}
             * The list of company IDs the user is allowed to connect to.
             */
            allowed_ids: Object.values(allowedCompanies).map((c) => c.id),

            /**
             * @type {Array.<number>}
             * The list of company IDs the user is connected to (selected in the company
             * switcher dropdown).
             */
            active_ids: activeCompanyIds,

            /**
             * @type {number}
             * The ID of the main company selected (the one highlighted in the company switcher
             * dropdown and displayed in the navbar of the webclient).
             */
            active_id: activeCompanyIds[0],

            /**
             * @param {(Array.<number>|number)} ids - id or ids of companies
             * @param {string} field - property of the company. Note that the properties of the
             *                          companies are those sent by the server in the session info.
             * @param {*} value - specified value
             * @returns {boolean}
             * returns a boolean indicating whether there's a company with id in `ids` for which
             * `field` matches the given `value`.
             */
            has: (ids, field, value) => {
                ids = typeof ids === "number" ? [ids] : ids || [];
                return Object.values(allowedCompanies).some(
                    (c) => ids.includes(c.id) && c[field] === value
                );
            },
        };
        allowedFns.add(evalContext.has);

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

            get isMultiCompany() {
                return Object.values(allowedCompanies).length > 1;
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

                function addCompanies(companyIds) {
                    for (const companyId of companyIds) {
                        if (!newCompanyIds.includes(companyId)) {
                            newCompanyIds.push(companyId);
                            addCompanies(allowedCompanies[companyId].child_ids);
                        }
                    }
                }

                if (includeChildCompanies) {
                    addCompanies(
                        companyIds.flatMap((companyId) => allowedCompanies[companyId].child_ids)
                    );
                }

                cookie.set("cids", newCompanyIds.join(CIDS_SEPARATOR));
                user.updateContext({ allowed_company_ids: newCompanyIds });

                const controller = action.currentController;
                const state = {};
                const options = { reload: true };
                if (controller?.props.resId && controller?.props.resModel) {
                    const hasReadRights = await user.checkAccessRight(
                        controller.props.resModel,
                        "read",
                        controller.props.resId
                    );

                    if (!hasReadRights) {
                        options.replace = true;
                        state.actionStack = router.current.actionStack.slice(0, -1);
                    }
                }

                router.pushState(state, options);
            },
            evalContext,
        };
    },
};

registry.category("services").add("company", companyService);
