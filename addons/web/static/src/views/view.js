/** @odoo-module **/

import { evaluateExpr } from "@web/core/py_js/py";
import { registry } from "@web/core/registry";
import { KeepLast } from "@web/core/utils/concurrency";
import { useService } from "@web/core/utils/hooks";
import { deepCopy } from "@web/core/utils/objects";
import { WithSearch } from "@web/search/with_search/with_search";
import { useActionLinks } from "@web/views/helpers/view_hook";
import { extractLayoutComponents } from "@web/views/layout";

const viewRegistry = registry.category("views");

const { Component, hooks } = owl;
const { useSubEnv } = hooks;

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

    "display",
    "globalState",

    "activateFavorite",

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
            config: { ...(this.env.config || {}) },
        });
        useActionLinks({ resModel });
    }

    async willStart() {
        // determine view type
        let ViewClass = viewRegistry.get(this.props.type);
        const type = ViewClass.type;

        // determine views for which descriptions should be obtained
        let { viewId, searchViewId } = this.props;

        const views = deepCopy(this.env.config.views || []);
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
        let { arch, fields, searchViewArch, searchViewFields, irFilters, actionMenus } = this.props;

        let loadView = !arch || (!actionMenus && loadActionMenus);
        let loadSearchView =
            (searchViewId !== undefined && !searchViewArch) || (!irFilters && loadIrFilters);

        let viewDescription = { viewId, resModel, type };
        let searchViewDescription;
        if (loadView || loadSearchView) {
            // view description (or search view description if required) is incomplete
            // a loadViews is done to complete the missing information
            const viewDescriptions = await this.viewService.loadViews(
                { context, resModel, views },
                { actionId: this.env.config.actionId, loadActionMenus, loadIrFilters }
            );
            // Note: if this.props.views is different from views, the cached descriptions
            // will certainly not be reused! (but for the standard flow this will work as
            // before)
            viewDescription = viewDescriptions[type];
            view[0] = viewDescription.viewId;
            searchViewDescription = viewDescriptions.search;
            if (loadSearchView) {
                searchViewId = searchViewId || searchViewDescription.viewId;
                if (!searchViewArch) {
                    searchViewArch = searchViewDescription.arch;
                    searchViewFields = searchViewDescription.fields;
                }
                if (!irFilters) {
                    irFilters = searchViewDescription.irFilters;
                }
            }
            this.env.config.views = views;
        }

        if (!arch) {
            arch = viewDescription.arch;
            fields = viewDescription.fields;
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
        if (subType) {
            ViewClass = viewRegistry.get(subType);
        }

        Object.assign(this.env.config, {
            viewId: viewDescription.viewId,
            viewType: type,
            viewSubType: subType,
            bannerRoute,
            ...extractLayoutComponents(ViewClass),
        });

        // prepare the view props
        const viewProps = {
            info: { actionMenus, mode: this.props.display.mode },
            arch,
            fields,
            resModel,
            useSampleModel: false,
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
        if (noContentHelp !== undefined) {
            const htmlHelp = document.createElement("div");
            htmlHelp.innerHTML = noContentHelp;
            if (htmlHelp.innerText.trim()) {
                viewProps.info.noContentHelp = noContentHelp;
            }
        }

        // prepare the WithSearch component props
        this.withSearchProps = {
            ...this.props,
            Component: ViewClass,
            componentProps: viewProps,
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
                ViewClass.searchMenuTypes ||
                this.constructor.searchMenuTypes;
        }

        for (const key in this.withSearchProps) {
            if (!(key in WithSearch.props)) {
                delete this.withSearchProps[key];
            }
        }
    }

    async willUpdateProps(nextProps) {
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
