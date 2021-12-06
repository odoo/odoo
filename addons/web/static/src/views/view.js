/** @odoo-module **/

import { evaluateExpr } from "@web/core/py_js/py";
import { registry } from "@web/core/registry";
import { KeepLast } from "@web/core/utils/concurrency";
import { useService } from "@web/core/utils/hooks";
import { deepCopy } from "@web/core/utils/objects";
import { extractLayoutComponents } from "@web/search/layout";
import { WithSearch } from "@web/search/with_search/with_search";
import { useActionLinks } from "@web/views/helpers/view_hook";

const { Component, onWillUpdateProps, onWillStart, toRaw, useSubEnv } = owl;
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
        breadcrumbs: [
            {
                get name() {
                    return displayName;
                },
            },
        ],
        getDisplayName: () => displayName,
        getPagerProps: () => {},
        historyBack: () => {},
        setDisplayName: (newDisplayName) => {
            displayName = newDisplayName;
        },
        viewSwitcherEntries: [],
        views: [],
    };
    return config;
}

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
 *  @property {string[]} [orderBy]
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
 *  @property {string[]} [searchMenuTypes]
 *  @property {Object} [globalState]
 */

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
    "searchMenuTypes",

    // LEGACY: remove this later (clean when mappings old state <-> new state are established)
    "searchPanel",
    "searchModel",
];

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
        });

        this.handleActionLinks = useActionLinks({ resModel });

        onWillStart(this.onWillStart);
        onWillUpdateProps(this.onWillUpdateProps);
    }

    async onWillStart() {
        // determine view type
        let descr = viewRegistry.get(this.props.type);
        const type = descr.type;

        // determine views for which descriptions should be obtained
        let { viewId, searchViewId } = this.props;

        const views = deepCopy(this.props.views || this.env.config.views);
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
        const { context, resModel, loadActionMenus, loadIrFilters } = this.props;
        let {
            arch,
            fields,
            relatedModels,
            searchViewArch,
            searchViewFields,
            irFilters,
            actionMenus,
        } = this.props;

        let loadView = !arch || (!actionMenus && loadActionMenus);
        let loadSearchView =
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
            // Note: if this.props.views is different from views, the cached descriptions
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
            fields = fields || result.fields;
            relatedModels = relatedModels || result.relatedModels;
        }

        if (!arch) {
            arch = viewDescription.arch;
        }
        if (!actionMenus) {
            actionMenus = viewDescription.actionMenus;
        }

        const parser = new DOMParser();
        const xml = parser.parseFromString(arch, "text/xml");
        const rootNode = xml.documentElement;

        const subType = rootNode.getAttribute("js_class");
        const bannerRoute = rootNode.getAttribute("banner_route");
        const sample = rootNode.getAttribute("sample");

        // determine ViewClass to instantiate (if not already done)
        // if (subType) {
        //     descr = viewRegistry.get(subType);
        // }

        Object.assign(this.env.config, {
            viewId: viewDescription.id,
            viewType: type,
            viewSubType: subType,
            bannerRoute,
            ...extractLayoutComponents(descr),
        });

        // prepare the view props
        const viewProps = {
            info: { actionMenus, mode: this.props.display.mode },
            arch,
            fields,
            relatedModels,
            resModel,
            useSampleModel: false,
            className: `${this.props.className} o_view_controller o_${this.env.config.viewType}_view`,
        };
        if (this.props.globalState) {
            viewProps.globalState = this.props.globalState;
        }

        if ("useSampleModel" in this.props) {
            viewProps.useSampleModel = this.props.useSampleModel;
        } else if (sample) {
            viewProps.useSampleModel = Boolean(evaluateExpr(sample));
        }

        for (const key in this.props) {
            if (!STANDARD_PROPS.includes(key)) {
                viewProps[key] = this.props[key];
            }
        }

        let { noContentHelp } = this.props;
        if (noContentHelp) {
            viewProps.info.noContentHelp = noContentHelp;
        }

        const finalProps = descr.props ? descr.props(viewProps, descr, this.env.config) : viewProps;
        // prepare the WithSearch component props
        this.withSearchProps = {
            ...toRaw(this.props),
            Component: descr.Controller,
            SearchModel: descr.SearchModel,
            componentProps: finalProps,
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

        if (!this.withSearchProps.searchMenuTypes) {
            this.withSearchProps.searchMenuTypes =
                this.props.searchMenuTypes ||
                descr.searchMenuTypes ||
                this.constructor.searchMenuTypes;
        }

        if (ViewClass.display) {
            // FIXME: there's something inelegant here: display might come from
            // the View's defaultProps, in which case, modifying it in place
            // would have unwanted effects.
            const display = { ...this.withSearchProps.display };
            for (const key in ViewClass.display) {
                if (typeof display[key] === "object") {
                    Object.assign(display[key], ViewClass.display[key]);
                } else if (!(key in display) || display[key]) {
                    display[key] = ViewClass.display[key];
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

    async onWillUpdateProps(nextProps) {
        // we assume that nextProps can only vary in the search keys:
        // comparison, context, domain, groupBy, orderBy
        const { comparison, context, domain, groupBy, orderBy } = nextProps;
        Object.assign(this.withSearchProps, { comparison, context, domain, groupBy, orderBy });
    }
}

View.template = "web.View";
View.components = { WithSearch };
View.defaultProps = {
    display: {},
    context: {},
    loadActionMenus: false,
    loadIrFilters: false,
    className: "",
};

View.searchMenuTypes = ["filter", "groupBy", "favorite"];

/** @todo rework doc */

// - create a fakeORM service? --> use sampleServer and mockServer parts?

// - action service uses View comp --> see if things cannot be simplified (we will use also maybe a ClientAction comp similar to view)

// - see if we want to simplify things related to callback recorders --> the class should be put elsewhere too (maybe in core along registry?)

/**
 * To manage (how?):
 *
  Relate to search
      searchModel // search model state (searchItems, query)
      searchPanel // search panel component state (expanded (hierarchy), scrollbar)

  Related to config/display/layout
      breadcrumbs
      withBreadcrumbs // 'no_breadcrumbs' in context ? !context.no_breadcrumbs : true,
      withControlPanel // this.withControlPanel from constructor
      withSearchBar // 'no_breadcrumbs' in context ? !context.no_breadcrumbs : true,
      withSearchPanel // this.withSearchPanel from constructor
      search_panel // = params.search_panel or context.search_panel

  Prepare for concrete view ???
      activeActions

  Do stuff in View comp ???
      banner // from arch = this.arch.attrs.banner_route
*/
