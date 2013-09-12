(function () {
    'use strict';

    var globalEditor;

    var website = openerp.website;
    website.templates.push('/website/static/src/xml/website.ace.xml');

    website.EditorBar.include({
        events: _.extend({}, website.EditorBar.prototype.events, {
            'click a[data-action=ace]': 'launchAce',
        }),
        launchAce: function () {
            if (globalEditor) {
                globalEditor.open();
            } else {
                globalEditor = new website.ace.ViewEditor(this);
                globalEditor.appendTo($(document.body));
            }
        },
    });

    website.ace = {};

    website.ace.XmlDocument = openerp.Class.extend({
        init: function (text) {
            this.xml = text;
        },
        isWellFormed: function () {
            try {
                if (document.implementation.createDocument) {
                    var dom = new DOMParser().parseFromString(this.xml, "text/xml");
                    return dom.getElementsByTagName("parsererror").length === 0;
                } else if (window.ActiveXObject) {
                    // TODO test in IE
                    var msDom = new ActiveXObject("Microsoft.XMLDOM");
                    msDom.async = false;
                    return !msDom.loadXML(this.xml);
                } else {
                    throw Error("Not implemented");
                }
            } catch(exception) {
                console.log(exception);
            }
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
            'change #ace-view-list': 'displayView',
            'click button[data-action=save]': 'saveView',
            'click button[data-action=format]': 'formatXml',
            'click button[data-action=close]': 'close',
        },
        start: function () {
            var self = this;
            var viewId = $(document.documentElement).data('view-xmlid');
            openerp.jsonRpc('/website/customize_template_get', 'call', {
                'xml_id': viewId,
                'optional': false,
            }).then(function (views) {
                self.loadViewList.call(self, views);
            });
            this.$el.hover();
        },
        selectedViewId: function () {
            return parseInt(this.$('#ace-view-list').val(), 10);
        },
        loadViewList: function (views) {
            var activeViews = _.filter(views, function (view) {
               return view.active;
            });
            var $viewList = this.$('#ace-view-list');
            _.each(activeViews, function (view) {
                if (view.id) {
                    new website.ace.ViewOption(this, view).appendTo($viewList);
                }
            });
            var editor = ace.edit(this.$('#ace-view-editor')[0]);
            editor.setTheme("ace/theme/monokai");
            this.aceEditor = editor;
            this.open();
        },
        displayView: function () {
            var editor = this.aceEditor;
            openerp.jsonRpc('/web/dataset/call', 'call', {
                model: 'ir.ui.view',
                method: 'read',
                args: [[this.selectedViewId()], ['arch'], website.get_context()],
            }).then(function(result) {
                if (result && result.length > 0) {
                    var xml = new website.ace.XmlDocument(result[0].arch)
                    var editingSession = new ace.EditSession(xml.xml);
                    editingSession.setMode("ace/mode/xml");
                    editingSession.setUndoManager(new ace.UndoManager());
                    editor.setSession(editingSession);
                } else {
                    throw Error("Could not load view XML");
                }
            });
        },
        formatXml: function () {
            var xml = new website.ace.XmlDocument(this.aceEditor.getValue());
            this.aceEditor.setValue(xml.format());
        },
        saveView: function () {
            var self = this;
            var xml = new website.ace.XmlDocument(this.aceEditor.getValue());
            if (xml.isWellFormed()) {
                openerp.jsonRpc('/web/dataset/call', 'call', {
                    model: 'ir.ui.view',
                    method: 'write',
                    args: [[this.selectedViewId()], { 'arch':  xml.xml }, website.get_context()],
                }).then(function(result) {
                    self.reloadPage();
                }).fail(function (error) {
                    self.displayError(error);
                });
            } else {
                self.displayError();
            }
        },
        reloadPage: function () {
            // TODO Reload { header + div#wrap + footer } only
            window.location.reload();
        },
        displayError: function (error) {
            // TODO Improve feedback (e.g. update 'Save' button + tooltip)
            alert("Malformed XML document");
        },
        open: function () {
            this.$el.removeClass('oe_ace_closed').addClass('oe_ace_open');
            this.displayView();
        },
        close: function () {
            var self = this;
            this.$el.bind('transitionend webkitTransitionEnd oTransitionEnd MSTransitionEnd', function () {
                globalEditor = null;
                self.destroy.call(self);
            }).removeClass('oe_ace_open').addClass('oe_ace_closed');
        },
    });

})();
