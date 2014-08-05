(function () {
    'use strict';

    var _t = openerp._t;
    var hash = "#advanced-view-editor";

    var website = openerp.website;
    website.add_template_file('/website/static/src/xml/website.ace.xml');

    website.Ace = openerp.Widget.extend({
        launchAce: function (e) {
            if (e) {
                e.preventDefault();
            }
            if (this.globalEditor) {
                this.globalEditor.open();
            } else {
                this.globalEditor = new website.ace.ViewEditor(this);
                this.globalEditor.appendTo($(document.body));
            }
        },
    });

    website.ace = {};

    website.ace.XmlDocument = openerp.Class.extend({
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

    website.ace.ViewOption = openerp.Widget.extend({
        template: 'website.ace_view_option',
        init: function (parent, options) {
            this.view_id = options.id;
            this.view_name = options.name;

            var indent = _.str.repeat("- ", options.level);
            this.view_name = _.str.sprintf("%s%s", indent, options.name);
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
            function resizeEditorHeight(height) {
                self.$el.css('top', height);
                self.$('.ace_editor').css('bottom', height);
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
            this.getParent().on('change:height', this, function (editor) {
                resizeEditorHeight(this.getParent().$el.outerHeight()+2);
            });
            resizeEditor(readEditorWidth());
            resizeEditorHeight(this.getParent().$el.outerHeight()+2);
        },
        loadTemplates: function () {
            var self = this;
            var args = {
                xml_id: $(document.documentElement).data('view-xmlid'),
                full: true,
                bundles: this.$('.js_include_bundles')[0].checked
            };
            return openerp
                .jsonRpc('/website/customize_template_get', 'call', args)
                .then(function (views) {
                    self.loadViews.call(self, views);
                    self.open.call(self);
                    var curentHash = window.location.hash;
                    var indexOfView = curentHash.indexOf("?view=");
                    if (indexOfView >= 0) {
                        var viewId = parseInt(curentHash.substring(indexOfView + 6, curentHash.length), 10);
                        self.$('#ace-view-list').val(viewId).change();
                    } else {
                        if (views.length >= 2) {
                            var mainTemplate = views[1];
                            self.$('#ace-view-list').val(mainTemplate.id).trigger('change');
                        }
                        window.location.hash = hash;
                    }
                });
        },
        loadViews: function (views) {
            var $viewList = this.$('#ace-view-list').empty();
            _(this.buildViewGraph(views)).each(function (view) {
                if (!view.id) { return; }

                this.views[view.id] = view;
                new website.ace.ViewOption(this, view).appendTo($viewList);
                this.loadView(view.id);
            }.bind(this));
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
                var parentId = view.inherit_id;
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
                this.$('#ace-view-id').text(_.str.sprintf(
                    _t("Template ID: %s"),
                    this.views[viewId].xml_id));
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
            var self = this;
            var xml = new website.ace.XmlDocument(session.text);
            var isWellFormed = xml.isWellFormed();
            var def = $.Deferred();
            if (isWellFormed === true) {
                openerp.jsonRpc('/web/dataset/call', 'call', {
                    model: 'ir.ui.view',
                    method: 'write',
                    args: [[session.id], { 'arch':  xml.xml }, website.get_context()],
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
        updateHash: function () {
            window.location.hash = hash + "?view=" + this.selectedViewId();
        },
        reloadPage: function () {
            this.updateHash();
            window.location.reload();
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
            function onchangeSession (e) {
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

            var $dialog = $(openerp.qweb.render('website.error_dialog', {
                title: session.text.match(/\s+name=['"]([^'"]+)['"]/i)[1],
                message:"<b>Malformed XML document</b>:<br/>" + message
            }));
            $dialog.appendTo("body");
            $dialog.modal('show');
        },
        open: function () {
            this.$el.removeClass('oe_ace_closed').addClass('oe_ace_open');
        },
        close: function () {
            window.location.hash = "";
            this.$el.removeClass('oe_ace_open').addClass('oe_ace_closed');
        },
    });

    website.ready().done(function() {
        var ace = new website.Ace();
        $(document.body).on('click', 'a[data-action=ace]', function() {
            ace.launchAce();
        });
    });

})();
