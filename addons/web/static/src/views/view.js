/** @odoo-module **/

import { evaluateExpr } from "@web/core/py_js/py";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/service_hook";
import { WithSearch } from "@web/search/with_search/with_search";

const viewRegistry = registry.category("views");

const { Component } = owl;

const STANDARD_PROPS = new Set([
    "actionFlags",
    "actionId",
    "context",
    "displayName",
    "domain",
    "groupBy",
    "loadActionMenus",
    "loadIrFilters",
    "noContentHelp",
    "resModel",
    "type",
    "views",
    "viewSwitcherEntries",
    "breadcrumbs",
    "useSampleModel",
    "searchViewId",
    "searchViewArch",
    "searchViewFields",
    "irFilters",
    "viewId",
    // LEGACY: remove this later
    "searchPanel",
    "searchModel",
    "searchState", // ?
]);

export class View extends Component {
    setup() {
        if (!("resModel" in this.props)) {
            throw Error(`View props should have a "resModel" key`);
        }
        if (!("type" in this.props)) {
            throw Error(`View props should have a "type" key`);
        }

        this.viewService = useService("view");

        this.withSearchProps = null;
    }

    async willStart() {
        // determine view type
        let ViewClass = viewRegistry.get(this.props.type);
        const type = ViewClass.type;

        // determine views for which descriptions should be obtained
        let { views, viewId, searchViewId } = this.props;

        views = JSON.parse(JSON.stringify(views));

        const view = views.find((v) => v[1] === type);
        if (view) {
            view[0] = viewId !== undefined ? viewId : view[0];
            viewId = view[0];
        } else {
            views.push([viewId || false, type]); // viewId will remain undefined if not specified and loadView=false
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
        const { actionId, context, resModel, loadActionMenus, loadIrFilters } = this.props;
        let viewDescription = { resModel, type };
        let searchViewDescription;
        let { arch, fields, searchViewArch, searchViewFields, irFilters, actionMenus } = this.props;

        let loadView = !arch || !fields || (!actionMenus && loadActionMenus);
        let loadSearchView =
            searchViewId !== undefined &&
            (!searchViewArch || !searchViewFields || (!irFilters && loadIrFilters));

        if (loadView || loadSearchView) {
            // view description (or search view description if required) is incomplete
            // a loadViews is done to complete the missing information
            const viewDescriptions = await this.viewService.loadViews(
                { context, resModel, views },
                { actionId, loadActionMenus, loadIrFilters }
            );
            // Note: if this.props.views is different from views, the cached descriptions
            // will certainly not be reused! (but for the standard flow this will work as
            // before)
            viewDescription = viewDescriptions[type];
            searchViewDescription = viewDescriptions.search;
            if (loadSearchView) {
                if (!searchViewArch) {
                    searchViewArch = searchViewDescription.arch;
                }
                if (!searchViewFields) {
                    searchViewFields = searchViewDescription.fields;
                }
                if (!irFilters) {
                    irFilters = searchViewDescription.irFilters;
                }
            }
        }

        if (arch) {
            viewDescription.arch = arch;
        }
        if (fields) {
            viewDescription.fields = fields;
        }
        if (actionMenus) {
            // good name for prop?
            viewDescription.actionMenus = actionMenus;
        }

        const parser = new DOMParser();
        const xml = parser.parseFromString(viewDescription.arch, "text/xml");
        const rootNode = xml.documentElement;
        const rootAttrs = {};
        for (const attrName of rootNode.getAttributeNames()) {
            rootAttrs[attrName] = rootNode.getAttribute(attrName);
        }

        //////////////////////////////////////////////////////////////////
        /** @todo take care of banner_route rootAttribute*/
        //////////////////////////////////////////////////////////////////

        // determine ViewClass to instantiate (if not already done)

        if (rootAttrs.js_class) {
            ViewClass = viewRegistry.get(rootAttrs.js_class);
        }

        // prepare the view props
        let viewProps = {
            info: {
                actionFlags: this.props.actionFlags,
                actionId: this.props.actionId,
                viewId: viewDescription.viewId,
                views,
                mode: this.props.display.mode,
                actionMenus: viewDescription.actionMenus,
                breadcrumbs: this.props.breadcrumbs,
                viewSwitcherEntries: this.props.viewSwitcherEntries,
                displayName: this.props.displayName,
                noContentHelp: null,
            },
            arch: viewDescription.arch,
            fields: viewDescription.fields,
            resModel,
            useSampleModel: false,
        };

        if ("useSampleModel" in this.props) {
            viewProps.useSampleModel = this.props.useSampleModel;
        } else if (rootAttrs.sample) {
            viewProps.useSampleModel = Boolean(evaluateExpr(rootAttrs.sample));
        }

        for (const key in this.props) {
            if (!STANDARD_PROPS.has(key)) {
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

        // prepare the WithSearh component props
        this.withSearchProps = {};
        for (const key in this.props) {
            this.withSearchProps[key] = this.props[key];
        }

        Object.assign(this.withSearchProps, {
            Component: ViewClass,
            componentProps: viewProps,
        });

        if (searchViewId !== undefined) {
            this.withSearchProps.searchViewId = searchViewId;
        }
        if (searchViewArch) {
            this.withSearchProps.searchViewArch = searchViewArch;
        }
        if (searchViewFields) {
            this.withSearchProps.searchViewFields = searchViewFields;
        }
        if (irFilters) {
            this.withSearchProps.irFilters = irFilters;
        }

        if (!this.withSearchProps.searchMenuTypes) {
            this.withSearchProps.searchMenuTypes =
                ViewClass.searchMenuTypes || this.constructor.searchMenuTypes;
        }

        //////////////////////////////////////////////////////////////////
        /** @todo prepare loadSearchPanel WithSearch prop (depends on view
         * types on searchpanel tag in search arch)                     */
        //////////////////////////////////////////////////////////////////

        if (searchViewArch) {
            // determine loadSearchPanel here and display
            // const DEFAULT_VIEW_TYPES = ["kanban", "list"];
            // if (node.hasAttribute("view_types")) {
            //   data.viewTypes.push(...node.getAttribute("view_types").split(","));
            // } else {
            //   data.viewTypes.push(...DEFAULT_VIEW_TYPES);
            // }
        }

        for (const key in this.withSearchProps) {
            if (!(key in WithSearch.props)) {
                delete this.withSearchProps[key];
            }
        }
    }

    async willUpdateProps(nextProps) {
        // we assume that nextProps can only vary in the search keys:
        // context, domain, domains, groupBy, orderBy
        const { context, domain, domains, groupBy, orderBy } = nextProps;
        Object.assign(this.withSearchProps, { context, domain, domains, groupBy, orderBy });
    }
}

View.template = "web.View";
View.components = { WithSearch };
View.defaultProps = {
    actionId: false,
    display: {},
    context: {},
    actionFlags: {},
    loadActionMenus: false,
    loadIrFilters: false,
    views: [],
};

View.searchMenuTypes = ["filter", "groupBy", "favorite"];

/** @todo rework doc */

/** @typedef {Object} ViewProps
 *  @property {string} resModel
 *  @property {string} type
 *  ...
 */

// export interface ViewProps {
//     // mandatory

//     resModel: string;
//     type: string;

//     // view description
//     arch?: string;
//     fields?: Object;
//     viewId?: number|false;

//     views?: Array[];

//     actionMenus?: Object;
//     loadActionMenus?: Boolean;

//     // search view description
//     searchViewArch?: string;
//     searchViewFields?: Object;
//     searchViewId?: number|false;

//     irFilters?: IrFilter[];
//     loadIrFilters?: Boolean;

//     // search query
//     context?: Object;
//     domain?: DomainRepr;
//     domains?: Object[]; // to rewok
//     groupBy?: string[];
//     orderBy?: string[];

//     // search state
//     __exportSearchState__?: CallbackRecorder;
//     searchState?: Object;

//     // others props manipulated by View or WithSearch
//     __saveParams__?: CallbackRecorder;
//     actionId?: number|false;
//     activateFavorite?: Boolean;
//     displayName?: string;
//     dynamicFilters?: Object[];
//     loadSearchPanel?: Boolean;
//     noContentHelp?: string;
//     searchMenuTypes?: string[];
//     useSampleModel?: Boolean;

//     // all props (sometimes modified like "views", "domain",...) to concrete view
//     // if it validate them (a filtering is done in case props validation is defined in concrete view)
//     [key:string]: any;
// }

/**
 * To manage:
 * 
  Relate to search
      searchModel // search model state (searchItems, query)
      searchPanel // search panel component state (expanded (hierarchy), scrollbar)

  Related to config/display/layout
      displayName // not exactly actionName,... action.display_name || action.name
      breadcrumbs
      withBreadcrumbs // 'no_breadcrumbs' in context ? !context.no_breadcrumbs : true,
      withControlPanel // this.withControlPanel from constructor
      withSearchBar // 'no_breadcrumbs' in context ? !context.no_breadcrumbs : true,
      withSearchPanel // this.withSearchPanel from constructor
      search_panel // = params.search_panel or context.search_panel

  Prepare for concrete view
      activeActions

  Do stuff in View comp
      banner // from arch = this.arch.attrs.banner_route
*/
