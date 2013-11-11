(function () {
    'use strict';

    var globalEditor;

    var hash = "#advanced-view-editor";

    var website = openerp.website;
    website.add_template_file('/website/static/src/xml/website.ace.xml');

    website.ready().then(function () {
        if (window.location.hash.indexOf(hash) >= 0) {
            launch();
        }
    });

    function launch () {
        if (globalEditor) {
            globalEditor.open();
        } else {
            globalEditor = new website.ace.ViewEditor();
            globalEditor.appendTo($(document.body));
        }
    }

    website.EditorBar.include({
        events: _.extend({}, website.EditorBar.prototype.events, {
            'click a[data-action=ace]': 'launchAce',
        }),
        launchAce: function (e) {
            e.preventDefault();
            launch();
        },
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
        resizing: false,
        refX: 0,
        minWidth: 40,
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

            var $editor = self.$('.ace_editor');
            function resizeEditor (target) {
                var width = Math.min(document.body.clientWidth, Math.max(parseInt(target, 10), self.minWidth));
                $editor.width(width);
                self.aceEditor.resize();
                self.$el.width(width);
            }
            function storeEditorWidth() {
                window.localStorage.setItem('ace_editor_width', self.$el.width());
            }
            function readEditorWidth() {
                var width = window.localStorage.getItem('ace_editor_width');
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
            document.body.addEventListener('mouseup', stopResizing, true);
            self.$('.ace_gutter').mouseup(stopResizing).mousedown(startResizing).click(stopResizing);
            $(document).mousemove(updateWidth);
            $('button[data-action=edit]').click(function () {
               self.close();
            });
            resizeEditor(readEditorWidth());
        },
        loadViews: function (views) {
            var self = this;
            var activeViews = _.uniq(_.filter(views, function (view) {
               return view.active;
            }), false, function (view) {
                return view.id;
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
                var editingSession = self.buffers[viewId] = new ace.EditSession(result[0].arch);
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
            this.updateHash();
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
            $.when.apply($, requests).then(function () {
                self.reloadPage.call(self);
            }).fail(function (source, error) {
                var message = (error.data.arguments[0] === "Access Denied") ? "Access denied: please sign in" : error.message;
                self.displayError.call(self, message);
            });
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
        updateHash: function () {
            window.location.hash = hash + "?view=" + this.selectedViewId();
        },
        reloadPage: function () {
            this.updateHash();
            window.location.reload();
        },
        displayError: function (error) {
            // TODO Improve feedback (e.g. update 'Save' button + tooltip)
            alert(error);
        },
        open: function () {
            this.$el.removeClass('oe_ace_closed').addClass('oe_ace_open');
            var curentHash = window.location.hash;
            var indexOfView = curentHash.indexOf("?view=");
            if (indexOfView >= 0) {
                var viewId = parseInt(curentHash.substring(indexOfView + 6, curentHash.length), 10);
                this.$('#ace-view-list').val(viewId).change();
            } else {
                window.location.hash = hash;
            }
        },
        close: function () {
            window.location.hash = "";
            this.$el.removeClass('oe_ace_open').addClass('oe_ace_closed');
        },
    });

})();
