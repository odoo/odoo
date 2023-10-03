/** @odoo-module **/

import { evaluateBooleanExpr } from "@web/core/py_js/py";
import { registry } from "@web/core/registry";
import { KeepLast } from "@web/core/utils/concurrency";
import { useService } from "@web/core/utils/hooks";
import { deepCopy, pick } from "@web/core/utils/objects";
import { nbsp } from "@web/core/utils/strings";
import { parseXML } from "@web/core/utils/xml";
import { extractLayoutComponents } from "@web/search/layout";
import { WithSearch } from "@web/search/with_search/with_search";
import { OnboardingBanner } from "@web/views/onboarding_banner";
import { useActionLinks } from "@web/views/view_hook";
import { computeViewClassName } from "./utils";
import {
    Component,
    markRaw,
    onWillUpdateProps,
    onWillStart,
    toRaw,
    useSubEnv,
    reactive,
} from "@odoo/owl";
const viewRegistry = registry.category("views");

/** @typedef {Object} Config
 *  @property {integer|false} actionId
 *  @property {string|false} actionType
 *  @property {Object} actionFlags
 *  @property {() => []} breadcrumbs
 *  @property {() => string} getDisplayName
 *  @property {(string) => void} setDisplayName
 *  @property {() => Object} getPagerProps
 *  @property {Object[]} viewSwitcherEntry
 *  @property {Object[]} viewSwitcherEntry
 *  @property {Component} Banner
 */

/**
 * Returns the default config to use if no config, or an incomplete config has
 * been provided in the env, which can happen with standalone views.
 * @returns {Config}
 */
export function getDefaultConfig() {
    let displayName;
    const config = {
        actionId: false,
        actionType: false,
        actionFlags: {},
        breadcrumbs: reactive([
            {
                get name() {
                    return displayName;
                },
            },
        ]),
        disableSearchBarAutofocus: false,
        getDisplayName: () => displayName,
        historyBack: () => {},
        pagerProps: {},
        setDisplayName: (newDisplayName) => {
            displayName = newDisplayName;
            // This is a hack to force the reactivity when a new displayName is set
            config.breadcrumbs.push(undefined);
            config.breadcrumbs.pop();
        },
        viewSwitcherEntries: [],
        views: [],
        Banner: OnboardingBanner,
    };
    return config;
}

/** @typedef {import("./utils").OrderTerm} OrderTerm */

/** @typedef {Object} ViewProps
 *  @property {string} resModel
 *  @property {string} type
 *
 *  @property {string} [arch] if given, fields must be given too /\ no post processing is done (evaluation of "groups" attribute,...)
 *  @property {Object} [fields] if given, arch must be given too
 *  @property {number|false} [viewId]
 *  @property {Object} [actionMenus]
 *  @property {boolean} [loadActionMenus=false]
 *
 *  @property {string} [searchViewArch] if given, searchViewFields must be given too
 *  @property {Object} [searchViewFields] if given, searchViewArch must be given too
 *  @property {number|false} [searchViewId]
 *  @property {Object[]} [irFilters]
 *  @property {boolean} [loadIrFilters=false]
 *
 *  @property {Object} [comparison]
 *  @property {Object} [context={}]
 *  @property {DomainRepr} [domain]
 *  @property {string[]} [groupBy]
 *  @property {OrderTerm[]} [orderBy]
 *
 *  @property {boolean} [useSampleModel]
 *  @property {string} [noContentHelp]
 *
 *  @property {Object} [display={}] to rework
 *
 *  manipulated by withSearch
 *
 *  @property {boolean} [activateFavorite]
 *  @property {Object[]} [dynamicFilters]
 *  @property {boolean} [hideCustomGroupBy]
 *  @property {string[]} [searchMenuTypes]
 *  @property {Object} [globalState]
 */

export class ViewNotFoundError extends Error {}

const CALLBACK_RECORDER_NAMES = [
    "__beforeLeave__",
    "__getGlobalState__",
    "__getLocalState__",
    "__getContext__",
    "__getOrderBy__",
];

const STANDARD_PROPS = [
    "resModel",
    "type",

    "arch",
    "fields",
    "relatedModels",
    "viewId",
    "actionMenus",
    "loadActionMenus",

    "searchViewArch",
    "searchViewFields",
    "searchViewId",
    "irFilters",
    "loadIrFilters",

    "comparison",
    "context",
    "domain",
    "groupBy",
    "orderBy",

    "useSampleModel",
    "noContentHelp",
    "className",

    "display",
    "globalState",

    "activateFavorite",
    "dynamicFilters",
    "hideCustomGroupBy",
    "searchMenuTypes",

    ...CALLBACK_RECORDER_NAMES,

    // LEGACY: remove this later (clean when mappings old state <-> new state are established)
    "searchPanel",
    "searchModel",
];

const ACTIONS = ["create", "delete", "edit", "group_create", "group_delete", "group_edit"];
export class View extends Component {
    setup() {
        const { arch, fields, resModel, searchViewArch, searchViewFields, type } = this.props;
        if (!resModel) {
            throw Error(`View props should have a "resModel" key`);
        }
        if (!type) {
            throw Error(`View props should have a "type" key`);
        }
        if ((arch && !fields) || (!arch && fields)) {
            throw new Error(`"arch" and "fields" props must be given together`);
        }
        if ((searchViewArch && !searchViewFields) || (!searchViewArch && searchViewFields)) {
            throw new Error(`"searchViewArch" and "searchViewFields" props must be given together`);
        }

        this.viewService = useService("view");
        this.withSearchProps = null;

        useSubEnv({
            keepLast: new KeepLast(),
            config: {
                ...getDefaultConfig(),
                ...this.env.config,
            },
            ...Object.fromEntries(
                CALLBACK_RECORDER_NAMES.map((name) => [name, this.props[name] || null])
            ),
        });

        this.handleActionLinks = useActionLinks({ resModel });

        onWillStart(() => this.loadView(this.props));
        onWillUpdateProps((nextProps) => this.onWillUpdateProps(nextProps));
    }

    async loadView(props) {
        // determine view type
        let descr = viewRegistry.get(props.type);
        const type = descr.type;

        // determine views for which descriptions should be obtained
        let { viewId, searchViewId } = props;

        const views = deepCopy(props.views || this.env.config.views);
        const view = views.find((v) => v[1] === type) || [];
        if (view.length) {
            view[0] = viewId !== undefined ? viewId : view[0];
            viewId = view[0];
        } else {
            view.push(viewId || false, type);
            views.push(view); // viewId will remain undefined if not specified and loadView=false
        }

        const searchView = views.find((v) => v[1] === "search");
        if (searchView) {
            searchView[0] = searchViewId !== undefined ? searchViewId : searchView[0];
            searchViewId = searchView[0];
        } else if (searchViewId !== undefined) {
            views.push([searchViewId, "search"]);
        }
        // searchViewId will remains undefined if loadSearchView=false

        // prepare view description
        const { context, resModel, loadActionMenus, loadIrFilters } = props;
        let {
            arch,
            fields,
            relatedModels,
            searchViewArch,
            searchViewFields,
            irFilters,
            actionMenus,
        } = props;

        const loadView = !arch || (!actionMenus && loadActionMenus);
        const loadSearchView =
            (searchViewId !== undefined && !searchViewArch) || (!irFilters && loadIrFilters);

        let viewDescription = { viewId, resModel, type };
        let searchViewDescription;
        if (loadView || loadSearchView) {
            // view description (or search view description if required) is incomplete
            // a loadViews is done to complete the missing information
            const result = await this.viewService.loadViews(
                { context, resModel, views },
                { actionId: this.env.config.actionId, loadActionMenus, loadIrFilters }
            );
            // Note: if props.views is different from views, the cached descriptions
            // will certainly not be reused! (but for the standard flow this will work as
            // before)
            viewDescription = result.views[type];
            searchViewDescription = result.views.search;
            if (loadSearchView) {
                searchViewId = searchViewId || searchViewDescription.id;
                if (!searchViewArch) {
                    searchViewArch = searchViewDescription.arch;
                    searchViewFields = result.fields;
                }
                if (!irFilters) {
                    irFilters = searchViewDescription.irFilters;
                }
            }
            this.env.config.views = views;
            fields = fields || markRaw(result.fields);
            relatedModels = relatedModels || markRaw(result.relatedModels);
        }

        if (!arch) {
            arch = viewDescription.arch;
        }
        if (!actionMenus) {
            actionMenus = viewDescription.actionMenus;
        }

        const archXmlDoc = parseXML(arch.replace(/&amp;nbsp;/g, nbsp));
        for (const action of ACTIONS) {
            if (action in this.props.context && !this.props.context[action]) {
                archXmlDoc.setAttribute(action, "0");
            }
        }

        let subType = archXmlDoc.getAttribute("js_class");
        const bannerRoute = archXmlDoc.getAttribute("banner_route");
        const sample = archXmlDoc.getAttribute("sample");
        const className = computeViewClassName(type, archXmlDoc, [
            "o_view_controller",
            ...(props.className || "").split(" "),
        ]);

        // determine ViewClass to instantiate (if not already done)
        if (subType) {
            if (viewRegistry.contains(subType)) {
                descr = viewRegistry.get(subType);
            } else {
                subType = null;
            }
        }

        Object.assign(this.env.config, {
            viewArch: archXmlDoc,
            viewId: viewDescription.id,
            viewType: type,
            viewSubType: subType,
            bannerRoute,
            noBreadcrumbs: props.noBreadcrumbs,
            ...extractLayoutComponents(descr),
        });
        const info = {
            actionMenus,
            mode: props.display.mode,
            irFilters,
            searchViewArch,
            searchViewFields,
            searchViewId,
        };

        // prepare the view props
        const viewProps = {
            info,
            arch: archXmlDoc,
            fields,
            relatedModels,
            resModel,
            useSampleModel: false,
            className,
        };
        if (viewDescription.custom_view_id) {
            // for dashboard
            viewProps.info.customViewId = viewDescription.custom_view_id;
        }
        if (props.globalState) {
            viewProps.globalState = props.globalState;
        }

        if ("useSampleModel" in props) {
            viewProps.useSampleModel = props.useSampleModel;
        } else if (sample) {
            viewProps.useSampleModel = evaluateBooleanExpr(sample);
        }

        for (const key in props) {
            if (!STANDARD_PROPS.includes(key)) {
                viewProps[key] = props[key];
            }
        }

        const { noContentHelp } = props;
        if (noContentHelp) {
            viewProps.info.noContentHelp = noContentHelp;
        }

        const searchMenuTypes =
            props.searchMenuTypes || descr.searchMenuTypes || this.constructor.searchMenuTypes;
        viewProps.searchMenuTypes = searchMenuTypes;

        const finalProps = descr.props ? descr.props(viewProps, descr, this.env.config) : viewProps;
        // prepare the WithSearch component props
        this.Controller = descr.Controller;
        this.componentProps = finalProps;
        this.withSearchProps = {
            ...toRaw(props),
            hideCustomGroupBy: props.hideCustomGroupBy || descr.hideCustomGroupBy,
            searchMenuTypes,
            SearchModel: descr.SearchModel,
        };

        if (searchViewId !== undefined) {
            this.withSearchProps.searchViewId = searchViewId;
        }
        if (searchViewArch) {
            this.withSearchProps.searchViewArch = searchViewArch;
            this.withSearchProps.searchViewFields = searchViewFields;
        }
        if (irFilters) {
            this.withSearchProps.irFilters = irFilters;
        }

        if (descr.display) {
            // FIXME: there's something inelegant here: display might come from
            // the View's defaultProps, in which case, modifying it in place
            // would have unwanted effects.
            const viewDisplay = deepCopy(descr.display);
            const display = { ...this.withSearchProps.display };
            for (const key in viewDisplay) {
                if (typeof display[key] === "object") {
                    Object.assign(display[key], viewDisplay[key]);
                } else if (!(key in display) || display[key]) {
                    display[key] = viewDisplay[key];
                }
            }
            this.withSearchProps.display = display;
        }

        for (const key in this.withSearchProps) {
            if (!(key in WithSearch.props)) {
                delete this.withSearchProps[key];
            }
        }
    }

    onWillUpdateProps(nextProps) {
        const oldProps = pick(this.props, "arch", "type", "resModel");
        const newProps = pick(nextProps, "arch", "type", "resModel");
        if (JSON.stringify(oldProps) !== JSON.stringify(newProps)) {
            return this.loadView(nextProps);
        }
        // we assume that nextProps can only vary in the search keys:
        // comparison, context, domain, groupBy, orderBy
        const { comparison, context, domain, groupBy, orderBy } = nextProps;
        Object.assign(this.withSearchProps, { comparison, context, domain, groupBy, orderBy });
    }
}

View._download = async function () {};

View.template = "web.View";
View.components = { WithSearch };
View.defaultProps = {
    display: {},
    context: {},
    loadActionMenus: false,
    loadIrFilters: false,
    className: "",
};
View.props = {
    "*": true,
};
View.searchMenuTypes = ["filter", "groupBy", "favorite"];
