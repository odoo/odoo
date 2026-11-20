/** @odoo-module **/

import { HierarchyNavbar } from "./hierarchy_navbar";
import { Layout } from "@web/search/layout";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useEffect, useState } from "@odoo/owl";

export class ViewHierarchy extends Component {
    setup() {
        this.action = useService("action");
        this.orm = useService("orm");
        this.router = useService("router");
        this.state = useState({ showInactive: false, searchedView: {}, viewTree: {} });
        this.websites = useState({ names: new Set(["All Websites"]), selected: "All Websites" });
        this.viewId = this.props.action.context.active_id || this.router.current.hash.active_id;
        this.hideGenericViewByWebsite = {};

        onWillStart(async () => {
            ({
                sibling_views: this.siblingViews,
                hierarchy: this.state.viewTree,
            } = await this.orm.call("ir.ui.view", "get_view_hierarchy", [this.viewId], {}));

            this.setupWebsiteNames();
            this.setupHideGenericViewByWebsite();
            this.linkViewsToParent();
        });

        useEffect(
            (searchFoundElem) => {
                if (searchFoundElem) {
                    searchFoundElem.scrollIntoView({ behavior: "smooth", block: "center" });
                }
            },
            () => [document.querySelector(".o_search_found")]
        );
    }

    /**
     * Filter the treeView by website
     * @param {String} websiteName
     */
    selectWebsite(websiteName) {
        this.websites.selected = websiteName;
    }

    /**
     * Show/hide inactive views
     * @param {Boolean} checked
     */
    toggleInactive(checked) {
        this.state.showInactive = checked;
    }

    /**
     * @param {String} keyword
     * @returns {Array} a list of visible views that match the keyword
     * insensitive case.
     * The comparison is done on the name, the key and the id of each views.
     * Priority is given to the exact matches and then to the order
     */
    getSearchResults(keyword) {
        const exactMatches = [];
        const matches = [];
        const lowercaseKeyword = keyword.toLowerCase();
        this.viewTraversal(
            this.state.viewTree,
            (currentView) => {
                if (
                    this.isViewDisplayed(currentView) &&
                    (currentView.name.toLowerCase() === lowercaseKeyword ||
                        currentView.key.toLowerCase() === lowercaseKeyword ||
                        currentView.id === parseInt(lowercaseKeyword))
                ) {
                    exactMatches.push(currentView);
                } else if (
                    this.isViewDisplayed(currentView) &&
                    (currentView.name.toLowerCase().includes(lowercaseKeyword) ||
                        currentView.key.toLowerCase().includes(lowercaseKeyword))
                ) {
                    matches.push(currentView);
                }
            },
            (currentView) => this.isViewDisplayed(currentView)
        );
        return exactMatches.concat(matches);
    }

    /**
     * Search the next visibile view that matches the keyword to the name, the
     * key and the id of the view
     * @param {String} keyword
     * @param {Boolean} forward
     */
    searchView(keyword, forward = true) {
        const matches = this.getSearchResults(keyword);
        let index = 0;
        if (this.state.searchedView.keyword === keyword) {
            index = matches.findIndex((view) => this.state.searchedView.id === view.id);
            index = forward ? index + 1 : index - 1;
            index = index - matches.length * Math.floor(index / matches.length);
        }

        const view = matches[index];
        if (view) {
            this.state.searchedView = {
                id: view.id,
                keyword: keyword,
                total: matches.length,
                index,
            };
        }
    }

    /**
     * Makes an inorder traversal of the view tree and apply a function at each
     * node
     * @param {Object} currentView represent the current view tree
     * @param {Function} fn function applied at each node with currentView as
     * parameter
     * @param {Function} continueRec take the view as argument and decide if
     * the recursion continue
     */
    viewTraversal(currentView, fn, continueRec = (view) => true) {
        fn(currentView);
        if (continueRec(currentView)) {
            currentView.inherit_children.forEach((childView) => {
                this.viewTraversal(childView, fn, continueRec);
            });
        }
    }

    /**
     * Setup website names from the viewTree into this.websites.names
     */
    setupWebsiteNames() {
        this.viewTraversal(this.state.viewTree, (currentView) => {
            if (currentView.website_name) {
                this.websites.names.add(currentView.website_name);
            }
        });
    }

    /**
     * States for each website filter if a generic view should be hided or not
     */
    setupHideGenericViewByWebsite() {
        this.viewTraversal(this.state.viewTree, (currentView) => {
            if (currentView.website_name) {
                if (!this.hideGenericViewByWebsite[currentView.website_name]) {
                    this.hideGenericViewByWebsite[currentView.website_name] = {};
                }
                this.hideGenericViewByWebsite[currentView.website_name][currentView.name] = true;
            }
        });
    }

    /**
     * Link views in the viewTree to their parent
     */
    linkViewsToParent() {
        this.viewTraversal(this.state.viewTree, (currentView) => {
            currentView.inherit_children.forEach((child) => (child.parent = currentView));
        });
    }

    /**
     * Collapse the view to show/hide the children
     * @param {Object} view
     */
    onCollapseClick(view) {
        view.collapsed = !view.collapsed;
        if (view.collapsed) {
            // When folding a parent, children should also fold
            this.viewTraversal(view, (child) => {
                child.collapsed = view.collapsed;
            });
        }
    }

    /**
     * @param {Object} view
     * @param {Boolean} isCollapsedDisplayed
     * @returns true if the view is displayed in the view tree, false otherwise
     */
    isViewDisplayed(view, isCollapsedDisplayed = false) {
        let isCollapsed = view.parent ? view.parent.collapsed : false;
        if (isCollapsedDisplayed) {
            isCollapsed = false;
        }
        const isActive = this.state.showInactive || view.active;
        const isWebsiteDisplayed =
            this.websites.selected === "All Websites" ||
            view.website_name === this.websites.selected ||
            (!view.website_name &&
                !this.hideGenericViewByWebsite[this.websites.selected][view.name]);
        return !isCollapsed && isActive && isWebsiteDisplayed;
    }

    /**
     * @param {Object} view
     * @returns true if view has a child to unfold, false otherwise
     */
    hasChildToUnfold(view) {
        return view.inherit_children.some((child) => this.isViewDisplayed(child, true));
    }

    /**
     * @param {Number} viewId
     */
    onShowDiffClick(viewId) {
        this.action.doAction("base.reset_view_arch_wizard_action", {
            additionalContext: {
                active_model: "ir.ui.view",
                active_ids: [viewId],
            },
        });
    }

    /**
     * @param {Number} viewId
     */
    openFormView(viewId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "ir.ui.view",
            res_id: viewId,
            views: [[false, "form"]],
        });
    }

    /**
     * @param {Number} viewId
     */
    onShowHierarchy(viewId) {
        this.action.doAction({
            type: "ir.actions.client",
            tag: "website_view_hierarchy",
            name: "View Hierarchy",
            context: {
                active_id: viewId,
            },
        });
    }
}

ViewHierarchy.components = { Layout, HierarchyNavbar };
ViewHierarchy.template = "website.view_hierarchy";

registry.category("actions").add("website_view_hierarchy", ViewHierarchy);
