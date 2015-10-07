odoo.define('website.ace', function (require) {
'use strict';

var ajax = require('web.ajax');
var Class = require('web.Class');
var core = require('web.core');
var Widget = require('web.Widget');
var base = require('web_editor.base');
var ace_call = require('website.ace_call');
var website = require('website.website');

var _t = core._t;
var qweb = core.qweb;

var hash = "#advanced-view-editor";

ajax.loadXML('/website/static/src/xml/website.ace.xml', qweb);

var Ace = Widget.extend({
    events: {
        'click a[data-action=ace]': 'launchAce',
    },
    start:function(){
        if(_.str.startsWith(window.location.hash, hash)){
            if($('.reset_less_style').css('display') == 'none'){
                this.launchAce();
            }else{
                $('.reset_less_style a').attr('href','/reset_style/'+window.location.hash);
            }
        }
        return this._super();
    },
    launchAce: function (e) {
        ace_call.load();

        if (e) {
            e.preventDefault();
        }
        if (this.globalEditor) {
            this.globalEditor.open();
        } else {
            this.globalEditor = new ViewEditor(this);
            this.globalEditor.appendTo($(document.body));
        }
    },
});

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

var ViewEditor = Widget.extend({
    resizing: false,
    refX: 0,
    minWidth: 100,
    template: 'website.ace_view_editor',
    events: {
        'change #ace-view-list-html': 'displaySelectedView',
        'change #ace-view-list-less': 'displaySelectedView',
        'change #ace-view-list-css': 'displaySelectedView',
        'click button[data-action=save]': 'saveViews',
        'click button[data-action=format]': 'formatXml',
        'click button[data-action=close]': 'close',
        'click button[data-action=reset]': 'reset',
        'click li a.type_switcher': 'change_type'
    },
    init: function (parent) {
        this.buffers = {'css':{},'less':{},'html':{}};
        this.views = {};
        this.active_list = '#ace-view-list-html';
        this.editor_type = "html";
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
            return parseInt(width || 800, 10);
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
        window.addEventListener('mouseup', stopResizing, true);
        self.$('.ace_gutter').mouseup(stopResizing).mousedown(startResizing).click(stopResizing);
        $(document).mousemove(updateWidth);
        $('button[data-action=edit]').click(function () {
           self.close();
        });
        this.getParent().on('change:height', this, function () {
            resizeEditorHeight(this.getParent().$el.outerHeight()+2);
        });
        resizeEditor(readEditorWidth());
        resizeEditorHeight(this.getParent().$el.outerHeight()+2);
    },
    loadTemplates: function () {
        var self = this;
        var args = {
            key: $(document.documentElement).data('view-xmlid'),
            full: true,
            bundles: !!$('script[src*=".assets_common"]').length
        };
        return ajax
            .jsonRpc('/website/get_editor_resources', 'call', args)
            .then(function (res) {
                var curentHash = window.location.hash;
                var indexOfView = curentHash.match(/.*\?view=(.*)/);
                var viewId = false;
                var views = res[self.editor_type]
                if (indexOfView && indexOfView[1]) {
                    viewId = indexOfView[1];
                    var type = _.last(viewId.split('.'));
                    if(type == 'css' || type == 'less'){
                        self.editor_type = type;
                        self.toggle_list();
                        views = res[self.editor_type];
                    }else{
                        viewId = parseInt(viewId, 10);
                    }
                    self.$('#ace-view-list-html').val(viewId).change();
                } else {
                    if (views.length >= 2) {
                        viewId = views[1].id;
                    }
                }
                self.res = res;
                self.loadViews(views);
                self.open();
                self.$(self.active_list).val(viewId).trigger('change');
                self.updateHash();
                //Hide options from editor if server returns empty list
                _.each(res, function(list, type){
                    if(list.length == 0){
                        self.$el.find('.type_switcher[data-edit-type="'+type+'"]').hide();
                    }
                });
            });
    },
    loadViews: function (views) {
        var self = this;
        if(this.editor_type == 'html'){
            var $viewList = this.$('#ace-view-list-html').empty();
            _(this.buildViewGraph(views)).each(function (view) {
                if (!view.id) { return; }
                this.views[view.id] = view;
                $viewList.append(_.str.sprintf('<option value="%s">%s%s</option>', view.id, _.str.repeat("- ", view.level), view.name));
                this.loadView(view.id);
            }.bind(this));
        }
        else{
            var $viewList = this.$(self.active_list).empty();
            _(views).each(function(url){
                var path = url.split("/");
                $viewList.append(_.str.sprintf('<option value="%s">%s</option>',url,path[path.length -1]));
                self.loadFiles(url,path[path.length -1])
            });
        }
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
        ajax.jsonRpc('/web/dataset/call', 'call', {
            model: 'ir.ui.view',
            method: 'read',
            args: [[viewId], ['arch'], _.extend(base.get_context(), {'lang': null})],
        }).then(function(result) {
            var editingSession = self.buffers[self.editor_type][viewId] = new ace.EditSession(result[0].arch);
            editingSession.setMode("ace/mode/xml");
            editingSession.setUndoManager(new ace.UndoManager());
            editingSession.on("change", function () {
                setTimeout(function () {
                    var $option = self.$(self.active_list).find('[value='+viewId+']');
                    var bufferName = $option.text();
                    var dirtyMarker = _t(" (unsaved changes)");
                    var isDirty = editingSession.getUndoManager().hasUndo();
                    if (isDirty && bufferName.indexOf(dirtyMarker) < 0) {
                        $option.text(bufferName + dirtyMarker);
                    } else if (!isDirty && bufferName.indexOf(dirtyMarker) > 0) {
                        $option.text(bufferName.substring(0, bufferName.indexOf(dirtyMarker)));
                    }
                }, 1);
            });
            if (viewId === self.selectedViewId()) {
                self.displayView(viewId);
            }
        });
    },
    loadFiles:function(url, name){
            var self = this;
            $.get(url, function(Content){
                var editingSession = self.buffers[self.editor_type][url] = new ace.EditSession(Content);
                editingSession.setMode("ace/mode/"+self.editor_type);
                editingSession.setUndoManager(new ace.UndoManager());
                editingSession.on("change", function () {
                    setTimeout(function () {
                        var $option = self.$(self.active_list).find('[value="'+url+'"]');
                        var bufferName = $option.text();
                        var dirtyMarker = _t(" (unsaved changes)");
                        var isDirty = editingSession.getUndoManager().hasUndo();
                        if (isDirty && bufferName.indexOf(dirtyMarker) < 0) {
                            $option.text(bufferName + dirtyMarker);
                        } else if (!isDirty && bufferName.indexOf(dirtyMarker) > 0) {
                            $option.text(bufferName.substring(0, bufferName.indexOf(dirtyMarker)));
                        }
                    }, 1);
                });
                if (url === self.selectedViewId()) {
                    self.displayView(url);
                }
            });
        },
    selectedViewId: function () {
         var self = this;
        if(this.editor_type == 'html')
            return parseInt(this.$('#ace-view-list-html').val(), 10);
        return this.$(self.active_list).val();
    },
    displayView: function (viewId) {
        var editingSession = this.buffers[this.editor_type][viewId];
        if (editingSession) {
            this.aceEditor.setSession(editingSession);
            if(this.editor_type == 'html'){
                this.$('#ace-view-id').text(_.str.sprintf(
                    _t("Template ID: %s"),
                    this.views[viewId].key));
            }else{
                this.$('#ace-view-id').text(_.str.sprintf(
                    _t("%s URL: %s"),
                    this.editor_type.toUpperCase(),viewId));
            }
        }
    },
    displaySelectedView: function () {
        this.displayView(this.selectedViewId());
        this.updateHash();
        this.check_customized();
    },
    formatXml: function () {
        if(this.editor_type == 'html'){
            var xml = new website.ace.XmlDocument(this.aceEditor.getValue());
            this.aceEditor.setValue(xml.format());
        }else{
            this.aceEditor.setValue(vkbeautify.css(this.aceEditor.getValue()));
        }
    },
    prepareSaveList:function(type){
        var self =this;
        return _.filter(_.map(self.buffers[type], function (editingSession, viewId) {
            if (type == 'html'){
                viewId = parseInt(viewId, 10);
            }
            return {
                id: viewId,
                isDirty: editingSession.getUndoManager().hasUndo(),
                text: editingSession.getValue(),
                doc_type:type
            };
        }), function (session) {
            return session.isDirty;
        });
    },
    saveViews: function () {
        var self = this;
        var toSave = [];
        _.each(self.buffers, function(num, key){ 
            toSave = toSave.concat(self.prepareSaveList(key));
        })
        this.clearError();
        var requests = _.map(toSave, function (session) {
            if(session.doc_type === 'html'){
                return self.saveView(session);
            }else{
                return self.saveAssets(session);
            }
        });
        $.when.apply($, requests).then(function () {
            self.reloadPage();
        }).fail(function (source, session, error) {
            self.displayError(source, session, error);
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
    saveAssets: function (session) {
        var self = this;
        var def = $.Deferred();
        ajax.jsonRpc('/website/save_asset', 'call', {
            'css': session,
        }).then(function (views) {
            def.resolve();
        }).fail(function (source, error) {
            def.reject("server", session, error);
        });
        return def;
    },
    updateHash: function () {
        window.location.hash = hash + "?view=" + this.selectedViewId();
    },
    reloadPage: function () {
        if(this.editor_type == 'html')
            this.updateHash();
        else if(! _.str.startsWith(this.selectedViewId(), '/custom/'))
            window.location.hash = hash + "?view=/custom" + this.selectedViewId();
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
        function onchangeSession () {
            self.aceEditor.off('changeSession', onchangeSession);
            gotoline();
        }

        var $list = this.$("#ace-view-list-html");
        if (+$list.val() == session.id) {
            if (line>-1) gotoline();
        } else {
            if (line) self.aceEditor.on('changeSession', onchangeSession);
            this.$("#ace-view-list-html").val(session.id).change();
        }

        var $dialog = $(qweb.render('website.error_dialog', {
            title: session.text.match(/\s+name=['"]([^'"]+)['"]/i)[1],
            message:"<b>Malformed XML document</b>:<br/>" + message
        }));
        $dialog.appendTo("body");
        $dialog.modal('show');
    },
    change_type:function(e){
        e.preventDefault();
        var self = this;
        this.editor_type = $(e.currentTarget).attr('data-edit-type');
        this.toggle_list();
        if(_.isEmpty(this.buffers[this.editor_type])){
            this.loadViews(this.res[this.editor_type]);
        }else{
            this.$(self.active_list).change();
        }
        this.updateHash();
        this.check_customized();
    },
    toggle_list:function(){
        var self = this;
        self.active_list = '#ace-view-list-'+self.editor_type;
        self.$el.find('.oe_view_list').addClass('hidden');
        $(self.active_list).removeClass('hidden');
        self.$el.find('.type_switcher_base').html($("[data-edit-type='"+self.editor_type+"']").html());
    },
    open: function () {
        this.$el.removeClass('oe_ace_closed').addClass('oe_ace_open');
    },
    close: function () {
        window.location.hash = "";
        this.$el.removeClass('oe_ace_open').addClass('oe_ace_closed');
    },
    check_customized:function(){
        var view = this.selectedViewId();
        var is_custom = this.editor_type != 'html' && view && view.lastIndexOf('/custom/', 0) === 0;
        $('.custom_ace_view').toggleClass('hidden', !is_custom);
    },
    reset: function () {
        var self = this;
        var $dialog = $(qweb.render('website.ace_editor.discard')).appendTo(document.body);
            $dialog.on('click', '.btn-danger', function () {
                ajax.jsonRpc('/website/remove_asset', 'call', {
                    'file_path': self.selectedViewId(),
                }).then(function (res) {
                    $dialog.remove();
                    self.reloadPage();
                    self.updateHash();
                    var selected_url = self.selectedViewId();
                     window.location.hash = hash + "?view=" + selected_url.substring(7, selected_url.length);
                });
            }).on('hidden.bs.modal', function () {
                $dialog.remove();
            });
            $dialog.modal('show');
    },
});

website.TopBar.include({
    start: function () {
        this.ace = new Ace();
        var def = this.ace.attachTo($('#html_editor'));
        return $.when(this._super(), def);
    }
});

});
