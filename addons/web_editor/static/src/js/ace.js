odoo.define('web_editor.ace', function (require) {
'use strict';

var ajax = require('web.ajax');
var Class = require('web.Class');
var core = require('web.core');
var Widget = require('web.Widget');
var base = require('web_editor.base');
var local_storage = require('web.local_storage');

var qweb = core.qweb;
var _t = core._t;

ajax.loadXML('/web_editor/static/src/xml/ace.xml', qweb);

var XmlDocument = Class.extend({
    init: function (text) {
        this.xml = text;
    },
    isWellFormed: function () {
        var error;
        if (document.implementation.createDocument) {
            // use try catch for ie
            try {
                var dom = new DOMParser().parseFromString(this.xml, "text/xml");
                error = dom.getElementsByTagName("parsererror");
                return error.length === 0 || $(error).text();
            } catch (e) {}
        }
        if (window.ActiveXObject) {
            // IE
            var msDom = new ActiveXObject("Microsoft.XMLDOM");
            msDom.async = false;
            msDom.loadXML(this.xml);
            return !msDom.parseError.errorCode || msDom.parseError.reason + "\nline " + msDom.parseError.line;
        }
        return true;
    },
    format: function () {
        return vkbeautify.xml(this.xml, 4);
    },
});

var ViewOption = Widget.extend({
    template: 'web_editor.ace_view_option',
    init: function (parent, options) {
        this.view_id = options.id;
        this.view_name = options.name;

        var indent = _.str.repeat("- ", options.level);
        this.view_name = _.str.sprintf("%s%s", indent, options.name);
        this._super(parent);
    },
});

var ViewEditor = Widget.extend({
    resizing: false,
    refX: 0,
    minWidth: 40,
    template: 'web_editor.ace_view_editor',
    events: {
        'change #ace-view-list': 'displaySelectedView',
        'click .js_include_bundles': 'loadTemplates',
        'click button[data-action=save]': 'saveViews',
        'click button[data-action=format]': 'formatXml',
        'click button[data-action=close]': 'close',
    },
    init: function (parent) {
        this.buffers = {};
        this.views = {};
        this._super(parent);
    },
    start: function () {
        var self = this;
        self.aceEditor = ace.edit(self.$('#ace-view-editor')[0]);
        self.aceEditor.setTheme("ace/theme/monokai");
        self.loadTemplates();

        var $editor = self.$('.ace_editor');
        function resizeEditor (target) {
            var width = Math.min(document.body.clientWidth, Math.max(parseInt(target, 10), self.minWidth));
            $editor.width(width);
            self.aceEditor.resize();
            self.$el.width(width);
        }
        function storeEditorWidth() {
            local_storage.setItem('ace_editor_width', self.$el.width());
        }
        function readEditorWidth() {
            var width = local_storage.getItem('ace_editor_width');
            return parseInt(width || 720, 10);
        }
        function startResizing (e) {
            self.refX = e.pageX;
            self.resizing = true;
        }
        function stopResizing () {
            self.resizing = false;
        }
        function updateWidth (e) {
            if (self.resizing) {
                var offset = e.pageX - self.refX;
                var width = self.$el.width() - offset;
                self.refX = e.pageX;
                resizeEditor(width);
                storeEditorWidth();
            }
        }
        self.$('.ace_gutter').mouseup(stopResizing).mousedown(startResizing).click(stopResizing);
        $(document).on("mousemove.ViewEditor", updateWidth).on("mouseup.ViewEditor", stopResizing);
        $('button[data-action=edit]').click(function () {
            self.close();
        });
        resizeEditor(readEditorWidth());

        return this._super.apply(this, arguments);
    },
    destroy: function () {
        this._super.apply(this, arguments);
        $(document).off(".ViewEditor");
    },

    // The 4 following methods are meant to be extended depending on the context
    open: function () {
        this.$el.removeClass('oe_ace_closed').addClass('oe_ace_open');
    },
    close: function () {
        this.$el.removeClass('oe_ace_open').addClass('oe_ace_closed');
    },
    reloadPage: function () {},
    loadTemplates: function () {},

    loadViews: function (views) {
        var $viewList = this.$('#ace-view-list').empty();
        var viewGraph = this.buildViewGraph(views);
        _(viewGraph).each(function (view) {
            if (!view.id) { return; }

            this.views[view.id] = view;
            new ViewOption(this, view).appendTo($viewList);
        }.bind(this));
        return this.loadView(viewGraph[0].id);
    },
    buildViewGraph: function (views) {
        var activeViews = _.uniq(_.filter(views, function (view) {
           return view.active;
        }), false, function (view) {
            return view.id;
        });
        var index = {};
        var roots = [];
        _.each(activeViews, function (view) {
            index[view.id] = view;
            view.children = [];
        });
        _.each(index, function (view) {
            var parentId = view.inherit_id[0];
            if (parentId && index[parentId]) {
                index[parentId].children.push(view);
            } else {
                roots.push(view);
            }
        });
        var result = [];
        function visit (node, level) {
            node.level = level;
            result.push(node);
            _.each(node.children, function (child) {
                visit(child, level + 1);
            });
        }
        _.each(roots, function (node) {
            visit(node, 0);
        });
        return result;
    },
    loadView: function (id) {
        var viewId = parseInt(id, 10);
        var self = this;
        return ajax.jsonRpc('/web/dataset/call', 'call', {
            model: 'ir.ui.view',
            method: 'read',
            args: [[viewId], ['arch'], _.extend(base.get_context(), {'lang': null})],
        }).then(function (result) {
            self._displayArch(result[0].arch, viewId);
        });
    },
    _displayArch: function(arch, viewId) {
        var self = this;
        var editingSession = this.buffers[viewId] = new ace.EditSession(arch);
        editingSession.setUseWorker(false);
        editingSession.setMode("ace/mode/xml");
        editingSession.setUndoManager(new ace.UndoManager());
        editingSession.on("change", function () {
            setTimeout(function () {
                var $option = self.$('#ace-view-list').find('[value='+viewId+']');
                var bufferName = $option.text();
                var dirtyMarker = " (unsaved changes)";
                var isDirty = editingSession.getUndoManager().hasUndo();
                if (isDirty && bufferName.indexOf(dirtyMarker) < 0) {
                    $option.text(bufferName + dirtyMarker);
                } else if (!isDirty && bufferName.indexOf(dirtyMarker) > 0) {
                    $option.text(bufferName.substring(0, bufferName.indexOf(dirtyMarker)));
                }
            }, 1);
        });
        if (viewId === self.selectedViewId()) {
            self.displayView.call(self, viewId);
        }
    },
    selectedViewId: function () {
        return parseInt(this.$('#ace-view-list').val(), 10);
    },
    displayView: function (id) {
        var viewId = parseInt(id, 10);
        var editingSession = this.buffers[viewId];
        if (editingSession) {
            this.aceEditor.setSession(editingSession);
            this.$('#ace-view-id').text(_.str.sprintf(
                _t("Template ID: %s"),
                this.views[viewId].xml_id));
        }
    },
    displaySelectedView: function () {
        var self = this;
        var viewID = this.selectedViewId();
        if (this.buffers[viewID]) {
            this.displayView(viewID);
            this.updateHash();
        } else {
            this.loadView(viewID).then(function() {
                self.updateHash();
            });
        }
    },
    formatXml: function () {
        var xml = new XmlDocument(this.aceEditor.getValue());
        this.aceEditor.setValue(xml.format());
    },
    saveViews: function () {
        var self = this;
        var toSave = _.filter(_.map(self.buffers, function (editingSession, viewId) {
            return {
                id: parseInt(viewId, 10),
                isDirty: editingSession.getUndoManager().hasUndo(),
                text: editingSession.getValue(),
            };
        }), function (session) {
            return session.isDirty;
        });
        this.clearError();
        var requests = _.map(toSave, function (session) {
            return self.saveView(session);
        });
        $.when.apply($, requests).then(function () {
            self.reloadPage.call(self);
        }).fail(function (source, session, error) {
            self.displayError.call(self, source, session, error);
        });
    },
    saveView: function (session) {
        var xml = new XmlDocument(session.text);
        var isWellFormed = xml.isWellFormed();
        var def = $.Deferred();
        if (isWellFormed === true) {
            ajax.jsonRpc('/web/dataset/call', 'call', {
                model: 'ir.ui.view',
                method: 'write',
                args: [[session.id], { 'arch':  xml.xml }, _.extend(base.get_context(), {'lang': null})],
            }).then(function () {
                def.resolve();
            }).fail(function (source, error) {
                def.reject("server", session, error);
            });
        } else {
            def.reject(null, session, isWellFormed);
        }
        return def;
    },
    clearError: function () {
        this.$(".ace_layer.ace_text-layer .ace_line").css("background", "");
    },
    displayError: function (source, session, error) {
        var self = this;
        var line, test;
        // format error message
        var message = _.isString(error) ? error
            : (error && error.data && error.data.arguments && error.data.arguments[0] === "Access Denied") ? "Access denied: please sign in"
            : (error && error.data && error.data.message) ? error.data.message
            : (error && error.message) ? error.message
            : "Unexpected error";
        if (source == "server") {
            message = eval(message.replace(/^\(/g, '([')
                .replace(/\)$/g, '])')
                .replace(/u'/g, "'")
                .replace(/<([^>]+)>/g, '<b style="color:#661100;">&lt;\$1&gt;</b>'))[1];
            line = -1;
        } else {
            line = message.match(/line ([0-9]+)/i);
            line = line ? parseInt(line[1],10) : -1;
            test = new RegExp("^\\s*"+line+"\\s*$");
        }

        function gotoline() {
            self.aceEditor.gotoLine(line);
            setTimeout(function () {
                var $lines = self.$(".ace_editor .ace_gutter .ace_gutter-cell");
                var index = $lines.filter(function () {
                    return test.test($(this).text());
                }).index();
                if (index>0) {
                    self.$(".ace_layer.ace_text-layer .ace_line:eq(" + index + ")").css("background", "#661100");
                }
            },100);
        }
        function onchangeSession () {
            self.aceEditor.off('changeSession', onchangeSession);
            gotoline();
        }

        var $list = this.$("#ace-view-list");
        if (+$list.val() == session.id) {
            if (line>-1) gotoline();
        } else {
            if (line) self.aceEditor.on('changeSession', onchangeSession);
            this.$("#ace-view-list").val(session.id).change();
        }
        return {
            title: session.text.match(/\s+name=['"]([^'"]+)['"]/i)[1],
            message: "<b>Malformed XML document</b>:<br/>" + message
        };
    },
});

return {
    XmlDocument: XmlDocument,
    ViewOption: ViewOption,
    ViewEditor: ViewEditor,
};

});
