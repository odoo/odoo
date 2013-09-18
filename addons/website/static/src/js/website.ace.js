(function () {
    'use strict';

    var globalEditor;

    var hash = "#advanced-view-editor";

    var website = openerp.website;
    website.templates.push('/website/static/src/xml/website.ace.xml');

    website.ready().then(function () {
        if (window.location.hash == hash) {
            launch();
        }
    });

    function launch () {
        if (globalEditor) {
            globalEditor.open();
        } else {
            globalEditor = new website.ace.ViewEditor(this);
            globalEditor.appendTo($(document.body));
        }
    }

    website.EditorBar.include({
        events: _.extend({}, website.EditorBar.prototype.events, {
            'click a[data-action=ace]': 'launch',
        }),
        launch: launch,
    });

    website.ace = {};

    website.ace.XmlDocument = openerp.Class.extend({
        init: function (text) {
            this.xml = text;
        },
        isWellFormed: function () {
            if (document.implementation.createDocument) {
                var dom = new DOMParser().parseFromString(this.xml, "text/xml");
                return dom.getElementsByTagName("parsererror").length === 0;
            } else if (window.ActiveXObject) {
                // TODO test in IE
                var msDom = new ActiveXObject("Microsoft.XMLDOM");
                msDom.async = false;
                return !msDom.loadXML(this.xml);
            }
            return true;
        },
        format: function () {
            return vkbeautify.xml(this.xml, 4);
        },
    });

    website.ace.ViewOption = openerp.Widget.extend({
        template: 'website.ace_view_option',
        init: function (parent, options) {
            this.view_id = options.id;
            this.view_name = options.name;
            this._super(parent);
        },
    });

    website.ace.ViewEditor = openerp.Widget.extend({
        template: 'website.ace_view_editor',
        events: {
            'change #ace-view-list': 'displaySelectedView',
            'click button[data-action=save]': 'saveViews',
            'click button[data-action=format]': 'formatXml',
            'click button[data-action=close]': 'close',
        },
        init: function (parent) {
            this.buffers = {};
            this._super(parent);
        },
        start: function () {
            var self = this;
            self.aceEditor = ace.edit(self.$('#ace-view-editor')[0]);
            self.aceEditor.setTheme("ace/theme/monokai");
            var viewId = $(document.documentElement).data('view-xmlid');
            openerp.jsonRpc('/website/customize_template_get', 'call', {
                'xml_id': viewId,
                'optional': false,
            }).then(function (views) {
                self.loadViews.call(self, views);
                self.open.call(self);
            });
        },
        loadViews: function (views) {
            var self = this;
            var activeViews = _.filter(views, function (view) {
               return view.active;
            });
            var $viewList = self.$('#ace-view-list');
            _.each(activeViews, function (view) {
                if (view.id) {
                    new website.ace.ViewOption(self, view).appendTo($viewList);
                    self.loadView(view.id);
                }
            });
        },
        loadView: function (id) {
            var viewId = parseInt(id, 10);
            var self = this;
            openerp.jsonRpc('/web/dataset/call', 'call', {
                model: 'ir.ui.view',
                method: 'read',
                args: [[viewId], ['arch'], website.get_context()],
            }).then(function(result) {
                var editingSession = self.buffers[viewId] = new ace.EditSession(result[0].arch);;
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
            });
        },
        selectedViewId: function () {
            return parseInt(this.$('#ace-view-list').val(), 10);
        },
        displayView: function (id) {
            var viewId = parseInt(id, 10);
            var editingSession = this.buffers[viewId];
            if (editingSession) {
                this.aceEditor.setSession(editingSession);
            }
        },
        displaySelectedView: function () {
            this.displayView(this.selectedViewId());
        },
        formatXml: function () {
            var xml = new website.ace.XmlDocument(this.aceEditor.getValue());
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
            var requests = _.map(toSave, self.saveView);
            $.when.apply($, requests).then(self.reloadPage).fail(self.displayError);
        },
        saveView: function (session) {
            var xml = new website.ace.XmlDocument(session.text);
            if (xml.isWellFormed()) {
                return openerp.jsonRpc('/web/dataset/call', 'call', {
                    model: 'ir.ui.view',
                    method: 'write',
                    args: [[session.id], { 'arch':  xml.xml }, website.get_context()],
                });
            } else {
                return $.Deferred().fail("Malformed XML document");
            }
        },
        reloadPage: function () {
            window.location.hash = hash;
            window.location.reload();
        },
        displayError: function (error) {
            // TODO Improve feedback (e.g. update 'Save' button + tooltip)
            alert(error);
        },
        open: function () {
            this.$el.removeClass('oe_ace_closed').addClass('oe_ace_open');
            this.displayView();
        },
        close: function () {
            window.location.hash = "";
            var self = this;
            this.$el.bind('transitionend webkitTransitionEnd oTransitionEnd MSTransitionEnd', function () {
                globalEditor = null;
                self.destroy.call(self);
            }).removeClass('oe_ace_open').addClass('oe_ace_closed');
        },
    });

})();
