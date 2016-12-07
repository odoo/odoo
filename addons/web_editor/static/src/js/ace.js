odoo.define('web_editor.ace', function (require) {
'use strict';

var ajax = require('web.ajax');
var core = require('web.core');
var Dialog = require("web.Dialog");
var Widget = require('web.Widget');
var base = require('web_editor.base');
var local_storage = require('web.local_storage');

var qweb = core.qweb;
var _t = core._t;

ajax.loadXML('/web_editor/static/src/xml/ace.xml', qweb);

function checkXML(xml) {
    if (typeof window.DOMParser != "undefined") {
        var xmlDoc = (new window.DOMParser()).parseFromString(xml, "text/xml");
        var error = xmlDoc.getElementsByTagName("parsererror");
        if (error.length > 0) {
            return {
                isValid: false,
                error: {
                    line: parseInt(error[0].innerHTML.match(/[Ll]ine[^\d]+(\d+)/)[1], 10),
                    message: error[0].innerHTML
                }
            };
        }
    } else if (typeof window.ActiveXObject != "undefined" && new window.ActiveXObject("Microsoft.XMLDOM")) {
        var xmlDocIE = new window.ActiveXObject("Microsoft.XMLDOM");
        xmlDocIE.async = "false";
        xmlDocIE.loadXML(xml);
        if (xmlDocIE.parseError.line > 0) {
            return {
                isValid: false,
                error: {
                    line: xmlDocIE.parseError.line,
                    message: xmlDocIE.parseError.reason
                }
            };
        }
    }

    return {
        isValid: true
    };
}

function formatXML(xml) {
    return window.vkbeautify.xml(xml, 4);
}

/**
 * The ViewEditor Widget allow to visualize resources (by default, XML views) and edit them.
 */
var ViewEditor = Widget.extend({
    template: 'web_editor.ace_view_editor',
    events: {
        'change #ace-view-list': function () {
            this.displayView(this.selectedViewId());
        },
        'click .js_include_bundles': function (e) {
            this.options.includeBundles = $(e.target).prop("checked");
            this.loadResources().then(this._updateViewSelectDOM.bind(this));
        },
        'click button[data-action=save]': 'saveResources',
        'click button[data-action=format]': 'formatResource',
        'click button[data-action=close]': 'do_hide',
    },
    /**
     * The init method should initialize the parameters of which information the ace editor will
     * have to load.
     * @param parent: the parent element of the editor widget.
     * @param viewKey: xml_id of the view whose linked resources are to be loaded.
                Also allow to receive the id directly.
     * @param options: an object containing some options
     *          - initialViewID: a specific view ID to load on start (otherwise the main view ID
     *              associated with the specified viewKey will be used).
     *          - includeBundles: whether or not the assets bundles templates needs to be loaded.
     */
    init: function (parent, viewKey, options) {
        this._super.apply(this, arguments);

        this.viewKey = viewKey;

        this.options = _.defaults({}, options, {position: 'right'});
        this.views = {};
        this.buffers = {};
    },
    /**
     * The willStart method is in charge of loading everything the ace library needs to work.
     * It also loads the resources to visualize. See @loadResources.
     */
    willStart: function () {
        var js_def = ajax.loadJS('/web/static/lib/ace/ace.odoo-custom.js').then(function () {
            return $.when(
                ajax.loadJS('/web/static/lib/ace/mode-xml.js'),
                ajax.loadJS('/web/static/lib/ace/theme-monokai.js')
            );
        });
        return $.when(this._super.apply(this, arguments), js_def, this.loadResources());
    },
    /**
     * The start method is in charge of initializing the library and initial view once the DOM is
     * ready. It also initializes the resize feature of the ace editor.
     * @return a deferred which is resolved when the widget DOM content is fully loaded.
     */
    start: function () {
        this.$viewEditor = this.$('#ace-view-editor');
        this.$editor = this.$(".ace_editor");
        this.$viewList = this.$('#ace-view-list');
        this.$viewID = this.$('#ace-view-id');

        this.aceEditor = window.ace.edit(this.$viewEditor[0]);
        this.aceEditor.setTheme("ace/theme/monokai");

        var refX = 0;
        var resizing = false;
        var minWidth = 400;
        var debounceStoreEditorWidth = _.debounce(storeEditorWidth, 500);

        this._updateViewSelectDOM();
        this.displayView(
            this.options.initialViewID
            || (typeof this.viewKey === "number" ? this.viewKey : _.findWhere(this.views, {xml_id: this.viewKey}).id)
        );

        $(document).on("mouseup.ViewEditor", stopResizing.bind(this)).on("mousemove.ViewEditor", updateWidth.bind(this));
        if (this.options.position === 'left') {
            this.$('.ace_scroller').after($('<div>').addClass('ace_resize_bar'));
            this.$('.ace_gutter').css({'cursor': 'default'});
            this.$el.on("mousedown.ViewEditor", ".ace_resize_bar", startResizing.bind(this));
        } else {
            this.$el.on("mousedown.ViewEditor", ".ace_gutter", startResizing.bind(this));
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
            local_storage.setItem('ace_editor_width', this.$el.width());
        }
        function readEditorWidth() {
            var width = local_storage.getItem('ace_editor_width');
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
     * The destroy method unbinds custom events binded to the document element.
     */
    destroy: function () {
        this._super.apply(this, arguments);
        this.$el.off(".ViewEditor");
        $(document).off(".ViewEditor");
    },
    /**
     * The loadResources method is in charge of loading data the ace editor will vizualize
     * and of processing them.
     * Default behavior is loading the activate views, index them and build their hierarchy.
     * @return a deferred which is resolved once everything is loaded and processed.
     */
    loadResources: function () {
        return ajax.jsonRpc("/web_editor/get_assets_editor_resources", "call", {
            key: this.viewKey,
            bundles: this.options.includeBundles
        }).then((function (views) {
            // Only keep the active views and index them by ID.
            this.views = _.indexBy(_.filter(views, function (view) {
                return view.active;
            }), "id");

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
            this.sorted_views = [];
            function visit(view, level) {
                view.level = level;
                self.sorted_views.push(view);
                _.each(view.children, function (child) {
                    visit(child, level + 1);
                });
            }
            _.each(roots, function (root) {
                visit(root, 0);
            });
        }).bind(this));
    },
    /**
     * The private _updateViewSelectDOM method purpose is to render the content of the view
     * select DOM element according to current widget data.
     */
    _updateViewSelectDOM: function () {
        var currentId = this.selectedViewId();

        var self = this;
        this.$viewList.empty();
        _.each(this.sorted_views, function (view) {
            self.$viewList.append($("<option/>", {
                value: view.id,
                text: _.str.sprintf("%s%s", _.str.repeat("- ", view.level), view.name),
                selected: currentId === view.id
            }));
        });
    },
    /**
     * The selectedViewId method returns the currently selected view id.
     * @return the currently selected view id.
     */
    selectedViewId: function () {
        return parseInt(this.$viewList.val(), 10);
    },
    /**
     * The displayView method forces the view identified by its ID to be displayed in the editor.
     * The method will update the view select DOM element as well.
     * @param viewID: the ID of the view to display.
     */
    displayView: function (viewID) {
        var editingSession = this.buffers[viewID];
        if (!editingSession) {
            editingSession = this._buildEditingSession(viewID);
        }
        this.aceEditor.setSession(editingSession);
        this.$viewID.text(_.str.sprintf(_t("Template ID: %s"), this.views[viewID].xml_id));

        if (viewID !== this.selectedViewId()) {
            this.$viewList.val(viewID);
        }
    },
    /**
     * The private _buildEditingSession method initialize a text editor for the specified view.
     * @param viewID: the ID of the view to display.
     * @return an ace.EditSession object linked to the specified viewID.
     */
    _buildEditingSession: function(viewID) {
        var self = this;
        var editingSession = this.buffers[viewID] = new window.ace.EditSession(this.views[viewID].arch);
        editingSession.setUseWorker(false);
        editingSession.setMode("ace/mode/xml");
        editingSession.setUndoManager(new window.ace.UndoManager());
        editingSession.on("change", function () {
            _.defer(function () {
                self._toggleDirtyInfo(viewID);
                self._showErrorLine();
            });
        });
        return editingSession;
    },
    /**
     * The private _toggleDirtyInfo method update the select option DOM element associated with
     * a particular viewID to indicate if the option is dirty or not.
     * @param viewID: the view id whose option has to be updated
     * @param isDirty: a boolean to indicate if the view is dirty or not ; default to content of UndoManager
     */
    _toggleDirtyInfo: function (viewID, isDirty) {
        if (!viewID || !this.buffers[viewID]) return;

        var $option = this.$viewList.find("[value=" + viewID + "]");
        var optionName = $option.text();
        var dirtyMarker = " (" + _t("unsaved changes") + ")";
        if (isDirty === undefined) {
            isDirty = this.buffers[viewID].getUndoManager().hasUndo();
        }
        if (isDirty && optionName.indexOf(dirtyMarker) < 0) {
            $option.text(optionName + dirtyMarker);
        } else if (!isDirty && optionName.indexOf(dirtyMarker) > 0) {
            $option.text(optionName.substring(0, optionName.indexOf(dirtyMarker)));
        }
    },
    /**
     * The formatResource method formats the current resource being vizualized.
     */
    formatResource: function () {
        this._formatXML();
    },
    /**
     * The private _formatXML method formats the current resource assuming it is an XML document.
     * If the xml is not valid, it shows the error instead.
     */
    _formatXML: function () {
        var xml = this.aceEditor.getValue();
        var check = checkXML(xml);
        if (check.isValid) {
            this.aceEditor.setValue(formatXML(xml));
        } else {
            this._showErrorLine(check.error.line, check.error.message, this.selectedViewId());
        }
    },
    /**
     * The saveResources method is in charge of saving every resource that has been modified.
     * If one cannot be saved, none is saved and an error message is displayed.
     * @return a deferred whose status indicates if the save is finished or if an error occured.
     */
    saveResources: function () {
        var dirtyBuffers = _.pick(this.buffers, function (session) {
            return session.getUndoManager().hasUndo();
        });
        var toSave = _.map(dirtyBuffers, function (editingSession, viewID) {
            return {
                id: parseInt(viewID, 10),
                text: editingSession.getValue(),
            };
        });

        this._showErrorLine();
        for (var i = 0 ; i < toSave.length ; i++) {
            var check = checkXML(toSave[i].text);
            if (!check.isValid) {
                this._showErrorLine(check.error.line, check.error.message, toSave[i].id);
                return $.Deferred().reject(toSave[i]);
            }
        }

        return $.when.apply($, _.map(toSave, this._saveView.bind(this))).fail(function (session, error) {
            Dialog.alert(this, "", {
                title: _t("Server error"),
                $content: $("<div/>").html(
                    _t("A server error occured. Please check you correctly signed in and that the XML you are saving is well-formed.")
                    + "<br/>"
                    + error
                )
            });
        });
    },
    /**
     * The private _saveView method is in charge of saving an unique XML view.
     * @param session: an object which contains the "id" and the "text" of the view to save.
     * @return a deferred whose status indicates if the save is finished or if an error occured.
     */
    _saveView: function (session) {
        var def = $.Deferred();

        var self = this;
        ajax.jsonRpc('/web/dataset/call', 'call', {
            model: 'ir.ui.view',
            method: 'write',
            args: [[session.id], {arch: session.text}, _.extend(base.get_context(), {lang: null})],
        }).then(function () {
            self._toggleDirtyInfo(session.id, false);
            def.resolve();
        }, function (source, error) {
            def.reject(session, error);
        });

        return def;
    },
    /**
     * The private _showErrorLine method is designed to show a line which produced an error. Red color
     * is added to the editor, the cursor move to the line and a message is opened on click on the line
     * number. If the _showErrorLine is called without argument, the effects are removed.
     * @param line: the line number to highlight
     * @param message: the message to show on click on the line number
     * @param viewID: the id of the view whose line is to highlight
     */
    _showErrorLine: function (line, message, viewID) {
        if (line === undefined || line <= 0) {
            if (this.$errorLine) {
                this.$errorLine.removeClass("o_error");
                this.$errorLine.off(".o_error");
                this.$errorLine = undefined;
                this.$errorContent.removeClass("o_error");
                this.$errorContent = undefined;
            }
            return;
        }

        if (this.selectedViewId() === viewID) {
            __showErrorLine.call(this, line);
        } else {
            var onChangeSession = (function () {
                this.aceEditor.off("changeSession", onChangeSession);
                _.delay(__showErrorLine.bind(this, line), 400);
            }).bind(this);
            this.aceEditor.on('changeSession', onChangeSession);
            this.displayView(viewID);
        }

        function __showErrorLine(line) {
            this.aceEditor.gotoLine(line);
            this.$errorLine = this.$viewEditor.find(".ace_gutter-cell").filter(function () {
                return parseInt($(this).text()) === line;
            }).addClass("o_error");
            this.$errorLine.addClass("o_error").on("click.o_error", function () {
                var $message = $("<div/>").html(message);
                $message.text($message.text());
                Dialog.alert(this, "", {$content: $message});
            });
            this.$errorContent = this.$viewEditor.find(".ace_scroller").addClass("o_error");
        }
    },
});

return ViewEditor;
});
