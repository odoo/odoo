odoo.define('project.PortalWebclientView', function (require) {
"use strict";

/**
 * Widget performing all common functions required to embed a "backend view" into a public portal,
 * along with some useful helper functions.
 * To embed a specific "backend view", any widget extending this should initialize the following
 * keys, before returning this._super.apply(this, arguments) (in init):
 * - this.accessToken  (str)
 * - this.actionXmlId  (str) (needed if requesting a search view as well)
 * - this.context  (Object)
 * - this.domain  (Array) (optional)
 * - this.is_website  (Boolean) (optional)
 * - this.model  (str)
 * - this.projectId  (number)
 * - this.taskId  (number) (optional)
 * - this.template  (str) (optional) /!\ view xmlID, not QWeb template
 * - this.templateEdit  (str) (optional) (same as above, in case of editing rights)
 * - this.viewType  (str)
 * - this.viewName  (str)
 */

var data = require('web.data');
var dataManager = require('web.data_manager');
var pyUtils = require('web.py_utils');
var rpc = require('web.rpc');
var SearchView = require('web.SearchView');
var Widget = require('web.Widget');

var PortalWebclientView = Widget.extend({
    init: function (parent, params) {
        this._super.apply(this, arguments);
        this._completeContext();
        /**
         * this.view will contain the "backend view" information:
         * - id (int)
         * - action (object) (if this.actionXmlId is specified)
         * - fvg (object)
         * - controller (Widget)
         */
        this.view = {};
        /**
         * if this.options.search is true, this.searchView will contain the search view information:
         * - fvg (object)
         * - controller (Widget)
         */
        this.searchView = {};

        // Redirect RPCs to public route with token check
        this._hijackRPCs(['web/dataset',
                          'web/action',
                          'mail/init_messaging'],
                         ['embed/project/dataset',
                          'embed/project/action',
                          'embed/project/mail/init_messaging'],
                         ['embed/project']);
    },
    willStart: function () {
        var self = this;
        this._super.apply(this, arguments);

        return this._checkAccess().then(function(accessRights) {
            if (accessRights === 'invalid') { // abort if no access rights
                return $.Deferred().reject(_("Access denied."));
            };
            return self._checkAccessCallback(accessRights); // get appropriate template
        }).then(function () {
            if (self.actionXmlId) { // get action if actionXmlId is specified
                return self._getAction(self.actionXmlId).then(function (action) {
                    action.domain = self.domain;
                    self.view['action'] = action;
                });
            };
        }).then(function () { // get the view's db id
            return self._getViewId();
        }).then(function (viewId) { // get the view's fvg
            self.view['id'] = viewId;
            return self._getViewInfo(self.view.id);
        }).then(function (viewInfo) { // get the view
            self.view['fvg'] = viewInfo[self.viewName];
            return self._getController(self.view.fvg,
                                       self.domain);
        }).then(function (controller) { // start and render the view
            self.view['controller'] = controller;
            return self.view.controller.appendTo($('<div/>'));
        }).then(function () { // get the search view and prepend it to the view if requested
            var $el = self.view.controller.$el;
            return self.options['search'] ? self._prependSearchViewTo($el) : $el;
        }).then(function ($el) { // make the view's $el this widget's $el + wire search view if requested
            self._replaceElement($el);
            if (self.searchView['controller']) {
                self.searchView.controller.on('search', self, self._onSearch);
            };  
        });
    },
    start: function () {
        return this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    renderElement: function () {
    },
    /**
     * Check the access rights of the user or their token and the privacy visibility setting of the project.
     * @param {string} accessToken (optional)
     * @param {number} projectId (optional)
     * @param {number} taskId (optional)
     * @returns {Deferred}: resolves to : - 'edit' if access token and/or settings allow edit
                                          - 'readonly' if access token and/or settings allow read only
                                          - 'invalid' if access token is invalid and user has no access
     */
    _checkAccess: function (accessToken, projectId, taskId) {
        accessToken = accessToken || this.accessToken;
        projectId = projectId || this.projectId;
        taskId = taskId || this.taskId;

        return this._rpc({
            route: '/embed/project/security/check_access',
            params: {
                'access_token': accessToken,
                'project_id': projectId,
                'task_id': taskId,
            },
        });
    },
    /**
     * Callback function for _checkAccess.
     * Its main purpose is to change the template if the editing rights are granted
     * and to allow overrides.
     *
     * @param {string} accessRights: - 'edit' if access token and/or settings allow edit
     *                               - 'readonly' if access token and/or settings allow read only
     *                               - 'invalid' (default) if access token is invalid and user has no access
     */
    _checkAccessCallback: function (accessRights) {
        this.accessRights = accessRights || 'invalid';
        this.template = this.accessRights === 'edit' ? this.templateEdit || this.template || '' : this.template || '';
    },
    /**
     * Make an artificial context object containing the active id and id,
     * This is required context information for elements in a view to be
     * added within the appropriate context.
     */
    _completeContext: function () {
        this.context['active_id'] = this.projectId;
        this.context['active_ids'] = [this.projectId];
        this.context['default_project_id'] = this.projectId;
        this.context['params'] = {
            active_id: this.projectId,
            id: this.taskId,
            model: this.model,
            view_type: this.viewType
        };
        this.context['search_default_project_id'] = [this.projectId];
        this.context['mail_notrack'] = true;
        this.context['mail_create_no_log'] = true;
    },
    /**
     * Get an action object from its XML ID
     *
     * @param {str} xmlId
     * @returns {Deferred} resolved with the action whose XML ID is xmlId
     */
    _getAction: function (xmlId) {
        return dataManager.load_action(xmlId, this.context);
    },
    /**
     * Create a controller for a given view, and make sure that
     * data and libraries are loaded.
     * /!\ Meant to be overriden: doesn't do anything out of the box.
     * Override to get the desired view's controller.
     *
     * @param {string[]} domain
     * @returns {Deferred} The deferred resolves to a controller
     */
    _getController: function (domain) {
        return $.when();
    },
    /**
     * Get a search view.
     *
     * @param {Object} params
     *  @param {String} params.model
     *  @param {Object} params.context
     *  @param {Array} params.views_descr array of [view_id, view_type]
     * @param {Object} options dictionary of various options:
     *     - options.action_id: the action_id (required),
     *     - options.disable_filters,
     *     - options.disable_groupby,
     *     - options.disable_favorites,
     * @returns {Deferred} The deferred resolves to a controller
     */
    _getSearchView: function(params, options) {
        var self = this;
        return dataManager.load_views(params, options).then(function (searchViewInfo) {
            self.searchView = {fvg: searchViewInfo['search']};
            var dataSet = new data.DataSetSearch(self,
                                                 self.model,
                                                 self.context,
                                                 self.domain);
            return new SearchView(self.view.controller,
                                  dataSet,
                                  self.searchView.fvg,
                                  options);
        });
    },
    /**
     * Fetches the requested view if a template is specified (this.template), or the default view
     * for this.model and this.viewType (primary view with the lowest priority).
     *
     * @returns {Deferred} The deferred resolves to a number
     */
    _getViewId: function () {
        var self = this;

        var method = 'get_view_id';
        // the python method override of the website module takes a 'xml_id' key instead of 'template'
        var kwargs = this.is_website ? {xml_id: this.template} : {template: this.template};
        // If no template is specified for the view, get the model's default view
        if (!this.template) {
            method = 'default_view';
            kwargs = {
                model: this.model,
                view_type: this.viewType,
            };
        };
        return this._rpc({
            route: '/embed/project/dataset/call_kw',
            params: {model: 'ir.ui.view',
                     method: method,
                     args: [],
                     kwargs: kwargs,
                     access_info: {
                        access_token: self.accessToken,
                        project_id: self.projectId,
                        task_id: self.taskId,
                     },
            },
        });
    },
    /**
     * Loads various information concerning views: fields_view for each view,
     * the fields of the corresponding model.
     *
     * @param {number} viewId
     * @param {string} viewName (optional)
     * @param {number} actionId (optional)
     * @returns {Deferred} The deferred resolves with the requested views information
     */
    _getViewInfo: function (viewId, viewName, actionId) {
        var viewName = viewName || this.viewName;
        var actionId = actionId || this.view.action ? this.view.action.id : undefined;
        var params = {
            context: this.context,
            model: this.model,
            views_descr: [[viewId, viewName]],
        };
        var options = {
            action_id: actionId,
        };
        return dataManager.load_views(params, options);
    },
    /**
     * Redirects all rpc's going from a given set of routes to another.
     * This is used to divert private routes to public ones with token/permission check.
     *
     * @param {string[]} from list of routes to redirect
     * @param {string[]} to list of routes to redirect to
     * from[i] redirects to to[i] so order matters and from.length === to.length
     * @param {string[]} doNotTouch (optional) list of paths to not touch
     */
    _hijackRPCs: function (from, to, doNotTouch) {
        var self = this;
        doNotTouch = doNotTouch || [];
        // Warning: dirty override of an object literal key
        rpc['originalBuildQuery'] = rpc.buildQuery;
        rpc.buildQuery = function (options) {
            var query = this.originalBuildQuery(options);
            // if the route contains one of the strings inside
            // doNotTouch, do not do anything
            for (var i = 0; i < doNotTouch.length; i++) {
                if (query.route.indexOf(doNotTouch[i]) !== -1) {
                    return query;
                };
            };
            // inject access_info into the params
            for (var i = 0; i < from.length; i++) {
                if (query.route.indexOf(from[i]) !== -1) {
                    query.params['access_info'] = {
                        access_token: self.accessToken,
                        project_id: self.projectId,
                        task_id: self.taskId,
                    };
                    // in a kanban view, you might be editing
                    // a task while being in the view of a project
                    if (self.currentlyEditedTask) {
                        query.params.access_info['task_id'] = self.currentlyEditedTask;
                        self.currentlyEditedTask = false;
                    };
                };
                // change the route
                query.route = query.route.replace(from[i], to[i]);
            };
            return query;
        };
        this.trigger_up('hijackRPCs');
    },
    /**
     * Method call when a search request is submitted. Fetches the results and reloads the view.
     *
     * @param {OdooEvent} event
     */
    _onSearch: function (event) {
        event.stopPropagation();
        // AAB: the id of the correct controller should be given in data
        _.extend(this.view.action,
                 this._processSearchData(this.view.action, event.data));
        this.view.controller.reload(_.extend({offset: 0},
                                    this.view.action));
    },
    /**
     * Gets a search view and prepends it to a given jQuery element.
     *
     * @param {JQuery} $el
     * @returns {Deferred} The deferred resolves with the updated element
     */
    _prependSearchViewTo: function ($el) {
        var self = this;

        var params = {
            context: this.context,
            model: this.model,
            views_descr: [[this.view.action.search_view_id[0], 'search']],
        };
        var options = {
            action_id: this.view.action.id,
            disable_filters: true,
            disable_groupby: true,
            disable_favorites: true,
        };
        return this._getSearchView(params, options).then(function (searchView) {
            searchView.action = self.view.action;
            self.searchView['controller'] = searchView;
            return self.searchView.controller.appendTo($('<div/>')).then(function() {
                self.searchView.controller.do_show();
                $el.prepend(self.searchView.controller.$el);
                return $el;
            });
        });
    },
    /**
     * Processes the search data sent by the search view.
     *
     * @private
     * @param {Object} action
     * @param {Object} searchData
     * @param {Object} [searchData.contexts=[]]
     * @param {Object} [searchData.domains=[]]
     * @param {Object} [searchData.groupbys=[]]
     * @returns {Object} an object with keys 'context', 'domain', 'groupBy'
     */
    _processSearchData: function (action, searchData) {
        var contexts = searchData.contexts;
        var domains = searchData.domains;
        var groupbys = searchData.groupbys;
        var action_context = action.context || {};
        var results = pyUtils.eval_domains_and_contexts({
            domains: [this.domain || []].concat(domains || []),
            contexts: [action_context].concat(contexts || []),
            group_by_seq: groupbys || [],
            eval_context: this.userContext,
        });
        var groupBy = results.group_by.length ?
                        results.group_by :
                        (action.context.group_by || []);
        groupBy = (typeof groupBy === 'string') ? [groupBy] : groupBy;

        if (results.error) {
            throw new Error(_.str.sprintf(_t("Failed to evaluate search criteria")+": \n%s",
                            JSON.stringify(results.error)));
        }

        var context = _.omit(results.context, 'time_ranges');

        return {
            context: context,
            domain: results.domain,
            groupBy: groupBy,
        };
    },
});

return PortalWebclientView;

});
