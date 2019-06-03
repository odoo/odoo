odoo.define('web_editor.ace', function (require) {
'use strict';

var ajax = require('web.ajax');
var config = require('web.config');
var concurrency = require('web.concurrency');
var core = require('web.core');
var Dialog = require('web.Dialog');
var Widget = require('web.Widget');
var localStorage = require('web.local_storage');

var _t = core._t;

/**
 * Formats a content-check result (@see checkXML, checkSCSS).
 *
 * @param {boolean} isValid
 * @param {integer} [errorLine] needed if isValid is false
 * @param {string} [errorMessage] needed if isValid is false
 * @returns {Object}
 */
function _getCheckReturn(isValid, errorLine, errorMessage) {
    return {
        isValid: isValid,
        error: isValid ? null : {
            line: errorLine,
            message: errorMessage,
        },
    };
}
/**
 * Checks the syntax validity of some XML.
 *
 * @param {string} xml
 * @returns {Object} @see _getCheckReturn
 */
function checkXML(xml) {
    if (typeof window.DOMParser != 'undefined') {
        var xmlDoc = (new window.DOMParser()).parseFromString(xml, 'text/xml');
        var error = xmlDoc.getElementsByTagName('parsererror');
        if (error.length > 0) {
            return _getCheckReturn(false, parseInt(error[0].innerHTML.match(/[Ll]ine[^\d]+(\d+)/)[1], 10), error[0].innerHTML);
        }
    } else if (typeof window.ActiveXObject != 'undefined' && new window.ActiveXObject('Microsoft.XMLDOM')) {
        var xmlDocIE = new window.ActiveXObject('Microsoft.XMLDOM');
        xmlDocIE.async = 'false';
        xmlDocIE.loadXML(xml);
        if (xmlDocIE.parseError.line > 0) {
            return _getCheckReturn(false, xmlDocIE.parseError.line, xmlDocIE.parseError.reason);
        }
    }
    return _getCheckReturn(true);
}
/**
 * Formats some XML so that it has proper indentation and structure.
 *
 * @param {string} xml
 * @returns {string} formatted xml
 */
function formatXML(xml) {
    // do nothing if an inline script is present to avoid breaking it
    if (/<script(?: [^>]*)?>[^<][\s\S]*<\/script>/i.test(xml)) {
        return xml;
    }
    return window.vkbeautify.xml(xml, 4);
}
/**
 * Checks the syntax validity of some SCSS.
 *
 * @param {string} scss
 * @returns {Object} @see _getCheckReturn
 */
var checkSCSS = (function () {
    var mapping = {
        '{': '}', '}': '{',
        '(': ')', ')': '(',
        '[': ']', ']': '[',
    };
    var openings = ['{', '(', '['];
    var closings = ['}', ')', ']'];

    return function (scss) {
        var stack = [];
        var line = 1;
        for (var i = 0 ; i < scss.length ; i++) {
            if (_.contains(openings, scss[i])) {
                stack.push(scss[i]);
            } else if (_.contains(closings, scss[i])) {
                if (stack.pop() !== mapping[scss[i]]) {
                    return _getCheckReturn(false, line, _t("Unexpected ") + scss[i]);
                }
            } else if (scss[i] === '\n') {
                line++;
            }
        }
        if (stack.length > 0) {
            return _getCheckReturn(false, line, _t("Expected ") + mapping[stack.pop()]);
        }
        return _getCheckReturn(true);
    };
})();
/**
 * Formats some SCSS so that it has proper indentation and structure.
 *
 * @todo Right now, this does return the given SCSS content, untouched.
 * @param {string} scss
 * @returns {string} formatted scss
 */
function formatSCSS(scss) {
    return scss;
}

/**
 * Allows to visualize resources (by default, XML views) and edit them.
 */
var ViewEditor = Widget.extend({
    template: 'web_editor.ace_view_editor',
    xmlDependencies: ['/web_editor/static/src/xml/ace.xml'],
    jsLibs: [
        '/web/static/lib/ace/ace.js',
        [
            '/web/static/lib/ace/javascript_highlight_rules.js',
            '/web/static/lib/ace/mode-xml.js',
            '/web/static/lib/ace/mode-scss.js',
            '/web/static/lib/ace/mode-js.js',
            '/web/static/lib/ace/theme-monokai.js'
        ]
    ],
    events: {
        'click .o_ace_type_switcher_choice': '_onTypeChoice',
        'change .o_res_list': '_onResChange',
        'click .o_ace_filter': '_onFilterChange',
        'click button[data-action=save]': '_onSaveClick',
        'click button[data-action=reset]': '_onResetClick',
        'click button[data-action=format]': '_onFormatClick',
        'click button[data-action=close]': '_onCloseClick',
        'click #ace-view-id > .alert-warning .close': '_onCloseWarningClick'
    },

    /**
     * Initializes the parameters so that the ace editor knows which information
     * it has to load.
     *
     * @constructor
     * @param {Widget} parent
     * @param {string|integer} viewKey
     *        xml_id or id of the view whose linked resources have to be loaded.
     * @param {Object} [options]
     * @param {string|integer} [options.initialResID]
     *        a specific view ID / SCSS URL to load on start (otherwise the main
     *        view ID associated with the specified viewKey will be used)
     * @param {string} [options.position=right]
     * @param {boolean} [options.doNotLoadViews=false]
     * @param {boolean} [options.doNotLoadSCSS=false]
     * @param {boolean} [options.doNotLoadJS=false]
     * @param {boolean} [options.includeBundles=false]
     * @param {string} [options.filesFilter=custom]
     * @param {string[]} [options.defaultBundlesRestriction]
     */
    init: function (parent, viewKey, options) {
        this._super.apply(this, arguments);

        this.context = options.context;

        this.viewKey = viewKey;
        this.options = _.defaults({}, options, {
            position: 'right',
            doNotLoadViews: false,
            doNotLoadSCSS: false,
            doNotLoadJS: false,
            includeBundles: false,
            filesFilter: 'custom',
            defaultBundlesRestriction: [],
        });

        this.resources = {xml: {}, scss: {}, js: {}};
        this.editingSessions = {xml: {}, scss: {}, js: {}};
        this.currentType = 'xml';

        // Alias
        this.views = this.resources.xml;
        this.scss = this.resources.scss;
        this.js = this.resources.js;
    },
    /**
     * Loads everything the ace library needs to work.
     * It also loads the resources to visualize (@see _loadResources).
     *
     * @override
     */
    willStart: function () {
        return Promise.all([
            this._super.apply(this, arguments),
            this._loadResources()
        ]);
    },
    /**
     * Initializes the library and initial view once the DOM is ready. It also
     * initializes the resize feature of the ace editor.
     *
     * @override
     */
    start: function () {
        this.$viewEditor = this.$('#ace-view-editor');

        this.$typeSwitcherChoices = this.$('.o_ace_type_switcher_choice');
        this.$typeSwitcherBtn = this.$('.o_ace_type_switcher > .dropdown-toggle');

        this.$lists = {
            xml: this.$('#ace-view-list'),
            scss: this.$('#ace-scss-list'),
            js: this.$('#ace-js-list'),
        };
        this.$includeBundlesArea = this.$('.oe_include_bundles');
        this.$includeAllSCSSArea = this.$('.o_include_all_scss');
        this.$viewID = this.$('#ace-view-id > span');
        this.$warningMessage = this.$('#ace-view-id > .alert-warning');

        this.$formatButton = this.$('button[data-action=format]');
        this.$resetButton = this.$('button[data-action=reset]');

        this.aceEditor = window.ace.edit(this.$viewEditor[0]);
        this.aceEditor.setTheme('ace/theme/monokai');
        this.$editor = this.$('.ace_editor');

        var refX = 0;
        var resizing = false;
        var minWidth = 400;
        var debounceStoreEditorWidth = _.debounce(storeEditorWidth, 500);

        this._updateViewSelectDOM();

        var initResID;
        var initType;
        if (this.options.initialResID) {
            initResID = this.options.initialResID;
            if (_.isString(initResID) && initResID[0] === '/') {
                if (_.str.endsWith(initResID, '.scss')) {
                    initType = 'scss';
                } else {
                    initType = 'js';
                }
            } else {
                initType = 'xml';
            }
        } else {
            if (!this.options.doNotLoadSCSS) {
                initResID = this.sortedSCSS[0][1][0].url; // first bundle, scss files, first one
                initType = 'scss';
            }
            if (!this.options.doNotLoadJS) {
                initResID = this.sortedJS[0][1][0].url; // first bundle, js files, first one
                initType = 'js';
            }
            if (!this.options.doNotLoadViews) {
                if (typeof this.viewKey === "number") {
                    initResID = this.viewKey;
                } else {
                    var view = _.findWhere(this.views, {xml_id: this.viewKey});
                    if (!view) {
                        view = _.findWhere(this.views, {key: this.viewKey});
                    }
                    initResID = view.id;
                }
                initType = 'xml';
            }
        }
        if (initResID) {
            this._displayResource(initResID, initType);
        }

        if (!this.sortedViews.length || !this.sortedSCSS.length) {
            _.defer((function () {
                this._switchType(this.sortedViews.length ? 'xml' : 'scss');
                this.$typeSwitcherBtn.parent('.btn-group').addClass('d-none');
            }).bind(this));
        }

        $(document).on('mouseup.ViewEditor', stopResizing.bind(this)).on('mousemove.ViewEditor', updateWidth.bind(this));
        if (this.options.position === 'left') {
            this.$('.ace_scroller').after($('<div>').addClass('ace_resize_bar'));
            this.$('.ace_gutter').css({'cursor': 'default'});
            this.$el.on('mousedown.ViewEditor', '.ace_resize_bar', startResizing.bind(this));
        } else {
            this.$el.on('mousedown.ViewEditor', '.ace_gutter', startResizing.bind(this));
        }

        resizeEditor.call(this, readEditorWidth.call(this));

        return this._super.apply(this, arguments);

        function resizeEditor(target) {
            var width = Math.min(document.body.clientWidth, Math.max(parseInt(target, 10), minWidth));
            this.$editor.width(width);
            this.aceEditor.resize();
            this.$el.width(width);
        }
        function storeEditorWidth() {
            localStorage.setItem('ace_editor_width', this.$el.width());
        }
        function readEditorWidth() {
            var width = localStorage.getItem('ace_editor_width');
            return parseInt(width || 720, 10);
        }
        function startResizing(e) {
            refX = e.pageX;
            resizing = true;
        }
        function stopResizing() {
            resizing = false;
        }
        function updateWidth(e) {
            if (!resizing) return;

            var offset = e.pageX - refX;
            if (this.options.position === 'left') {
                offset = - offset;
            }
            var width = this.$el.width() - offset;
            refX = e.pageX;
            resizeEditor.call(this, width);
            debounceStoreEditorWidth.call(this);
        }
    },
    /**
     * @override
     */
    destroy: function () {
        this._super.apply(this, arguments);
        this.$el.off('.ViewEditor');
        $(document).off('.ViewEditor');
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Initializes a text editor for the specified resource.
     *
     * @private
     * @param {integer|string} resID - the ID/URL of the view/scss/js file
     * @param {string} [type] (default to the currently selected one)
     * @returns {ace.EditSession}
     */
    _buildEditingSession: function (resID, type) {
        var self = this;
        type = type || this.currentType;
        var editingSession = new window.ace.EditSession(this.resources[type][resID].arch);
        editingSession.setUseWorker(false);
        editingSession.setMode('ace/mode/' + (type || this.currentType));
        editingSession.setUndoManager(new window.ace.UndoManager());
        editingSession.on('change', function () {
            _.defer(function () {
                self._toggleDirtyInfo(resID);
                self._showErrorLine();
            });
        });
        return editingSession;
    },
    /**
     * Forces the view/scss/js file identified by its ID/URL to be displayed in the
     * editor. The method will update the resource select DOM element as well if
     * necessary.
     *
     * @private
     * @param {integer|string} resID
     * @param {string} [type] - the type of resource (either 'xml', 'scss' or 'js')
     */
    _displayResource: function (resID, type) {
        if (type) {
            this._switchType(type);
        }

        var editingSession = this.editingSessions[this.currentType][resID];
        if (!editingSession) {
            editingSession = this.editingSessions[this.currentType][resID] = this._buildEditingSession(resID);
        }
        this.aceEditor.setSession(editingSession);

        var isCustomized = false;
        if (this.currentType === 'xml') {
            this.$viewID.text(_.str.sprintf(_t("Template ID: %s"), this.views[resID].key));
        } else if (this.currentType === 'scss') {
            isCustomized = this.scss[resID].customized;
            this.$viewID.text(_.str.sprintf(_t("SCSS file: %s"), resID));
        } else {
            isCustomized = this.js[resID].customized;
            this.$viewID.text(_.str.sprintf(_t("JS file: %s"), resID));
        }
        this.$lists[this.currentType].select2('val', resID);

        this.$resetButton.toggleClass('d-none', this.currentType === 'xml' || !isCustomized);

        // TODO the warning message is always shown for XML templates but:
        // 1) We have to implement a way to be able to reset XML templates
        //    otherwise the warning message is not accurate
        // 2) We should be able to detect if the XML template is customized to
        //    not show the warning in that case
        this.$warningMessage.toggleClass('d-none',
            this.currentType !== 'xml' && (resID.indexOf('/user_custom_') >= 0 || isCustomized));

        this.aceEditor.resize(true);
    },
    /**
     * Formats the current resource being vizualized.
     * (@see formatXML, formatSCSS)
     *
     * @private
     */
    _formatResource: function () {
        var res = this.aceEditor.getValue();
        var check = (this.currentType === 'xml' ? checkXML : checkSCSS)(res);
        if (check.isValid) {
            this.aceEditor.setValue((this.currentType === 'xml' ? formatXML : formatSCSS)(res));
        } else {
            this._showErrorLine(check.error.line, check.error.message, this._getSelectedResource());
        }
    },
    /**
     * Returns the currently selected resource data.
     *
     * @private
     * @returns {integer|string} view ID or scss file URL
     */
    _getSelectedResource: function () {
        var value = this.$lists[this.currentType].select2('val');
        return parseInt(value, 10) || value;
    },
    /**
     * Loads data the ace editor will vizualize and process it. Default behavior
     * is loading the activate views, index them and build their hierarchy.
     *
     * @private
     * @returns {Promise}
     */
    _loadResources: function () {
        // Reset resources
        this.resources = {xml: {}, scss: {}, js: {}};
        this.editingSessions = {xml: {}, scss: {}, js: {}};
        this.views = this.resources.xml;
        this.scss = this.resources.scss;
        this.js = this.resources.js;

        // Load resources
        return this._rpc({
            route: '/web_editor/get_assets_editor_resources',
            params: {
                key: this.viewKey,
                get_views: !this.options.doNotLoadViews,
                get_scss: !this.options.doNotLoadSCSS,
                get_js: !this.options.doNotLoadJS,
                bundles: this.options.includeBundles,
                bundles_restriction: this.options.filesFilter === 'all' ? [] : this.options.defaultBundlesRestriction,
                only_user_custom_files: this.options.filesFilter === 'custom',
            },
        }).then((function (resources) {
            _processViews.call(this, resources.views || []);
            _processJSorSCSS.call(this, resources.scss || [], 'scss');
            _processJSorSCSS.call(this, resources.js || [], 'js');
        }).bind(this));

        function _processViews(views) {
            // Only keep the active views and index them by ID.
            _.extend(this.views, _.indexBy(_.filter(views, function (view) {
                return view.active;
            }), 'id'));

            // Initialize a 0 level for each view and assign them an array containing their children.
            var self = this;
            var roots = [];
            _.each(this.views, function (view) {
                view.level = 0;
                view.children = [];
            });
            _.each(this.views, function (view) {
                var parentId = view.inherit_id[0];
                var parent = parentId && self.views[parentId];
                if (parent) {
                    parent.children.push(view);
                } else {
                    roots.push(view);
                }
            });

            // Assign the correct level based on children key and save a sorted array where
            // each view is followed by their children.
            this.sortedViews = [];
            function visit(view, level) {
                view.level = level;
                self.sortedViews.push(view);
                _.each(view.children, function (child) {
                    visit(child, level + 1);
                });
            }
            _.each(roots, function (root) {
                visit(root, 0);
            });
        }

        function _processJSorSCSS(data, type) {
            // The received scss or js data is already sorted by bundle and DOM order
            if (type === 'scss') {
                this.sortedSCSS = data;
            } else {
                this.sortedJS = data;
            }

            // Store the URL ungrouped by bundle and use the URL as key (resource ID)
            var resources = type === 'scss' ? this.scss : this.js;
            _.each(data, function (bundleInfos) {
                _.each(bundleInfos[1], function (info) { info.bundle_xmlid = bundleInfos[0].xmlid; });
                _.extend(resources, _.indexBy(bundleInfos[1], 'url'));
            });
        }
    },
    /**
     * Forces the view/scss/js file identified by its ID/URL to be reset to the way
     * it was before the user started editing it.
     *
     * @todo views reset is not supported yet
     *
     * @private
     * @param {integer|string} [resID] (default to the currently selected one)
     * @param {string} [type] (default to the currently selected one)
     * @returns {Promise}
     */
    _resetResource: function (resID, type) {
        resID = resID || this._getSelectedResource();
        type = type || this.currentType;

        if (this.currentType === 'xml') {
            return Promise.reject(_t("Reseting views is not supported yet"));
        } else {
            var resource = type === 'scss' ? this.scss[resID] : this.js[resID];
            return this._rpc({
                route: '/web_editor/reset_asset',
                params: {
                    url: resID,
                    bundle_xmlid: resource.bundle_xmlid,
                },
            });
        }
    },
    /**
     * Saves a unique SCSS or JS file.
     *
     * @private
     * @param {Object} session - contains the 'id' (url) and the 'text' of the
     *                         SCSS or JS file to save.
     * @return {Promise} status indicates if the save is finished or if an
     *                    error occured.
     */
    _saveSCSSorJS: function (session) {
        var self = this;
        var sessionIdEndsWithJS = _.string.endsWith(session.id, '.js');
        var bundleXmlID = sessionIdEndsWithJS ? this.js[session.id].bundle_xmlid : this.scss[session.id].bundle_xmlid;
        var fileType = sessionIdEndsWithJS ? 'js' : 'scss';
        return self._rpc({
            route: '/web_editor/save_asset',
            params: {
                url: session.id,
                bundle_xmlid: bundleXmlID,
                content: session.text,
                file_type: fileType,
            },
        }).then(function () {
            self._toggleDirtyInfo(session.id, fileType, false);
        });
    },
    /**
     * Saves every resource that has been modified. If one cannot be saved, none
     * is saved and an error message is displayed.
     *
     * @private
     * @return {Promise} status indicates if the save is finished or if an
     *                    error occured.
     */
    _saveResources: function () {
        var self = this;
        var toSave = {};
        var errorFound = false;
        _.each(this.editingSessions, (function (editingSessions, type) {
            if (errorFound) return;

            var dirtySessions = _.pick(editingSessions, function (session) {
                return session.getUndoManager().hasUndo();
            });
            toSave[type] = _.map(dirtySessions, function (session, resID) {
                return {
                    id: parseInt(resID, 10) || resID,
                    text: session.getValue(),
                };
            });

            this._showErrorLine();
            for (var i = 0 ; i < toSave[type].length && !errorFound ; i++) {
                var check = (type === 'xml' ? checkXML : checkSCSS)(toSave[type][i].text);
                if (!check.isValid) {
                    this._showErrorLine(check.error.line, check.error.message, toSave[type][i].id, type);
                    errorFound = toSave[type][i];
                }
            }
        }).bind(this));
        if (errorFound) return Promise.reject(errorFound);

        var defs = [];
        var mutex = new concurrency.Mutex();
        _.each(toSave, (function (_toSave, type) {
            // Child views first as COW on a parent would delete them
            _toSave = _.sortBy(_toSave, 'id').reverse();
            _.each(_toSave, function (session) {
                defs.push(mutex.exec(function () {
                    return (type === 'xml' ? self._saveView(session) : self._saveSCSSorJS(session));
                }));
            });
        }).bind(this));

        var self = this;
        return Promise.all(defs).guardedCatch(function (results) {
            var error = results[1];
            Dialog.alert(self, '', {
                title: _t("Server error"),
                $content: $('<div/>').html(
                    _t("A server error occured. Please check you correctly signed in and that the file you are saving is correctly formatted.")
                    + '<br/>'
                    + error
                )
            });
        });
    },
    /**
     * Saves an unique XML view.
     *
     * @private
     * @param {Object} session - the 'id' and the 'text' of the view to save.
     * @returns {Promise} status indicates if the save is finished or if an
     *                     error occured.
     */
    _saveView: function (session) {
        var self = this;
        return new Promise(function (resolve, reject) {
            self._rpc({
                model: 'ir.ui.view',
                method: 'write',
                args: [[session.id], {arch: session.text}],
            }, {
                noContextKeys: 'lang',
            }).then(function () {
                self._toggleDirtyInfo(session.id, 'xml', false);
                resolve();
            }, function (source, error) {
                reject(session, error);
            });
        });
    },
    /**
     * Shows a line which produced an error. Red color is added to the editor,
     * the cursor move to the line and a message is opened on click on the line
     * number. If called without argument, the effects are removed.
     *
     * @private
     * @param {integer} [line] - the line number to highlight
     * @param {string} [message] - to show on click on the line number
     * @param {integer|string} [resID]
     * @param {string} [type]
     */
    _showErrorLine: function (line, message, resID, type) {
        if (line === undefined || line <= 0) {
            if (this.$errorLine) {
                this.$errorLine.removeClass('o_error');
                this.$errorLine.off('.o_error');
                this.$errorLine = undefined;
                this.$errorContent.removeClass('o_error');
                this.$errorContent = undefined;
            }
            return;
        }

        if (type) this._switchType(type);

        if (this._getSelectedResource() === resID) {
            __showErrorLine.call(this, line);
        } else {
            var onChangeSession = (function () {
                this.aceEditor.off('changeSession', onChangeSession);
                _.delay(__showErrorLine.bind(this, line), 400);
            }).bind(this);
            this.aceEditor.on('changeSession', onChangeSession);
            this._displayResource(resID, this.currentType);
        }

        function __showErrorLine(line) {
            this.aceEditor.gotoLine(line);
            this.$errorLine = this.$viewEditor.find('.ace_gutter-cell').filter(function () {
                return parseInt($(this).text()) === line;
            }).addClass('o_error');
            this.$errorLine.addClass('o_error').on('click.o_error', function () {
                var $message = $('<div/>').html(message);
                $message.text($message.text());
                Dialog.alert(this, "", {$content: $message});
            });
            this.$errorContent = this.$viewEditor.find('.ace_scroller').addClass('o_error');
        }
    },
    /**
     * Switches to the SCSS, XML or JS edition. Calling this method will adapt all
     * DOM elements to keep the editor consistent.
     *
     * @private
     * @param {string} type - either 'xml', 'scss' or 'js'
     */
    _switchType: function (type) {
        this.currentType = type;
        this.$typeSwitcherBtn.html(this.$typeSwitcherChoices.filter('[data-type=' + type + ']').html());
        _.each(this.$lists, function ($list, _type) { $list.toggleClass('d-none', type !== _type); });
        this.$lists[type].change();

        this.$includeBundlesArea.toggleClass('d-none', this.currentType !== 'xml' || !config.isDebug());
        this.$includeAllSCSSArea.toggleClass('d-none', this.currentType !== 'scss' || !config.isDebug());
        this.$includeAllSCSSArea.find('[data-value="restricted"]').toggleClass('d-none', this.options.defaultBundlesRestriction.length === 0);
        this.$formatButton.toggleClass('d-none', this.currentType !== 'xml');
    },
    /**
     * Updates the select option DOM element associated with a particular resID
     * to indicate if the option is dirty or not.
     *
     * @private
     * @param {integer|string} resID
     * @param {string} [type] (default to the currently selected one)
     * @param {boolean} [isDirty] true if the view is dirty, default to content
     *                            of UndoManager
     */
    _toggleDirtyInfo: function (resID, type, isDirty) {
        type = type || this.currentType;

        if (!resID || !this.editingSessions[type][resID]) return;

        var $option = this.$lists[type].find('[value="' + resID + '"]');
        if (isDirty === undefined) {
            isDirty = this.editingSessions[type][resID].getUndoManager().hasUndo();
        }
        $option.data('dirty', isDirty);
    },
    /**
     * Renders the content of the view/file <select/> DOM element according to
     * current widget data.
     *
     * @private
     */
    _updateViewSelectDOM: function () {
        var currentId = this._getSelectedResource();

        var self = this;
        this.$lists.xml.empty();
        _.each(this.sortedViews, function (view) {
            self.$lists.xml.append($('<option/>', {
                value: view.id,
                text: view.name,
                selected: currentId === view.id,
                'data-level': view.level,
                'data-debug': view.xml_id,
            }));
        });

        this.$lists.scss.empty();
        _populateList(this.sortedSCSS, this.$lists.scss, 5);

        this.$lists.js.empty();
        _populateList(this.sortedJS, this.$lists.js, 3);

        this.$lists.xml.select2('destroy');
        this.$lists.xml.select2({
            formatResult: _formatDisplay.bind(this, false),
            formatSelection: _formatDisplay.bind(this, true),
        });
        this.$lists.xml.data('select2').dropdown.addClass('o_ace_select2_dropdown');
        this.$lists.scss.select2('destroy');
        this.$lists.scss.select2({
            formatResult: _formatDisplay.bind(this, false),
            formatSelection: _formatDisplay.bind(this, true),
        });
        this.$lists.scss.data('select2').dropdown.addClass('o_ace_select2_dropdown');
        this.$lists.js.select2('destroy');
        this.$lists.js.select2({
            formatResult: _formatDisplay.bind(this, false),
            formatSelection: _formatDisplay.bind(this, true),
        });
        this.$lists.js.data('select2').dropdown.addClass('o_ace_select2_dropdown');

        function _populateList(sortedData, $list, lettersToRemove) {
            _.each(sortedData, function (bundleInfos) {
                var $optgroup = $('<optgroup/>', {
                    label: bundleInfos[0].name,
                }).appendTo($list);
                _.each(bundleInfos[1], function (dataInfo) {
                    var name = dataInfo.url.substring(_.lastIndexOf(dataInfo.url, '/') + 1, dataInfo.url.length - lettersToRemove);
                    $optgroup.append($('<option/>', {
                        value: dataInfo.url,
                        text: name,
                        selected: currentId === dataInfo.url,
                        'data-debug': dataInfo.url,
                        'data-customized': dataInfo.customized
                    }));
                });
            });
        }

        function _formatDisplay(isSelected, data) {
            var $elem = $(data.element);

            var text = data.text || '';
            if (!isSelected) {
                text = Array(($elem.data('level') || 0) + 1).join('-') + ' ' + text;
            }
            var $div = $('<div/>',  {
                text: text,
                class: 'o_ace_select2_result',
            });

            if ($elem.data('dirty') || $elem.data('customized')) {
                $div.prepend($('<span/>', {
                    class: 'mr8 fa fa-floppy-o ' + ($elem.data('dirty') ? 'text-warning' : 'text-success'),
                }));
            }

            if (!isSelected && config.isDebug() && $elem.data('debug')) {
                $div.append($('<span/>', {
                    text: ' (' + $elem.data('debug') + ')',
                    class: 'ml4 small text-muted',
                }));
            }

            return $div;
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when the close button is clicked -> hides the ace editor.
     *
     * @private
     */
    _onCloseClick: function () {
        this.do_hide();
    },
    /**
     * Called when the format button is clicked -> format the current resource.
     *
     * @private
     */
    _onFormatClick: function () {
        this._formatResource();
    },
    /**
     * Called when a filter dropdown item is cliked. Reload the resources
     * according to the new filter and make it visually active.
     *
     * @private
     * @param {Event} ev
     */
    _onFilterChange: function (ev) {
        var $item = $(ev.target);
        $item.addClass('active').siblings().removeClass('active');
        if ($item.data('type') === 'xml') {
            this.options.includeBundles = $(ev.target).data('value') === 'all';
        } else {
            this.options.filesFilter = $item.data('value');
        }
        this._loadResources().then(this._updateViewSelectDOM.bind(this));
    },
    /**
     * Called when another resource is selected -> displays it.
     *
     * @private
     */
    _onResChange: function () {
        this._displayResource(this._getSelectedResource());
    },
    /**
     * Called when the reset button is clicked -> resets the resources to its
     * original standard odoo state.
     *
     * @private
     */
    _onResetClick: function () {
        var self = this;
        Dialog.confirm(this, _t("If you reset this file, all your customizations will be lost as it will be reverted to the default file."), {
            title: _t("Careful !"),
            confirm_callback: function () {
                self._resetResource(self._getSelectedResource());
            },
        });
    },
    /**
     * Called when the save button is clicked -> saves the dirty resources and
     * reloads.
     *
     * @private
     */
    _onSaveClick: function () {
        this._saveResources();
    },
    /**
     * Called when the user wants to switch from xml to scss or vice-versa ->
     * adapt resources choices and displays a resource of that type.
     *
     * @private
     * @param {Event} ev
     */
    _onTypeChoice: function (ev) {
        ev.preventDefault();
        this._switchType($(ev.target).data('type'));
    },
    /**
     * Allows to hide the warning message without removing it from the DOM
     * -> by default Bootstrap removes alert from the DOM
     */
    _onCloseWarningClick: function () {
        this.$warningMessage.addClass('d-none');
    },
});

return ViewEditor;
});
