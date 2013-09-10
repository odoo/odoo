(function () {
    'use strict';

    var editor = null;

    var website = openerp.website;
    website.templates.push('/website/static/src/xml/website.ace.xml');

    website.EditorBar.include({
        events: _.extend({}, website.EditorBar.prototype.events, {
            'click a[data-action=ace]': 'launchAce',
        }),
        launchAce: function () {
            if (!editor) {
                editor = new website.ace.ViewEditor();
                editor.appendTo($(document.body));
                setTimeout(function () {
                    editor.show.call(editor);
                }, 100);
            } else {
                editor.show();
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
            'click button[data-action=close]': 'hide',
        },
        start: function () {
            var self = this;
            var currentView = $(document.documentElement).data('view-xmlid');
            this.$viewList = this.$('#ace-view-list'),
            openerp.jsonRpc('/website/customize_template_get', 'call', { 'xml_id': currentView, 'optional': false })
                .then(function(result) {
                    _.each(result, function (view) {
                        if (view.id) {
                            new website.ace.ViewOption(self, view).appendTo(self.$viewList);
                        }
                    });
                    var editor = ace.edit(self.$('#ace-view-editor')[0]);
                    editor.setTheme("ace/theme/monokai");
                    self.aceEditor = editor;
                });
        },
        displayView: function () {
            var editor = this.aceEditor;
            openerp.jsonRpc('/web/dataset/call', 'call', {
                model: 'ir.ui.view',
                method: 'read',
                args: [[this.$viewList.val()], ['arch']]
            }).then(function(result) {
                var xml = new website.ace.XmlDocument(result[0].arch)
                var editingSession = new ace.EditSession(xml.xml);
                editingSession.setMode("ace/mode/xml");
                editingSession.setUndoManager(new ace.UndoManager());
                editor.setSession(editingSession);
            });
        },
        formatXml: function () {
            var xml = new website.ace.XmlDocument(this.aceEditor.getValue());
            this.aceEditor.setValue(xml.format());
        },
        saveView: function () {
            var xml = new website.ace.XmlDocument(this.aceEditor.getValue());
            if (xml.isWellFormed()) {
                openerp.jsonRpc('/web/dataset/call', 'call', {
                    model: 'ir.ui.view',
                    method: 'write',
                    args: [[this.$viewList.val()], { 'arch':  xml.xml }]
                }).then(function(result) {
                    window.location.reload();
                });
            } else {
                alert("Please check your XML structure!");
            }
        },
        hide: function () {
            this.$el.removeClass('oe_ace_open');
            this.$el.addClass('oe_ace_closed');
        },
        show: function () {
            this.$el.removeClass('oe_ace_closed');
            this.$el.addClass('oe_ace_open');
            this.displayView();
        },
        destroy: function () {
            editor = null;
            this._super();
        },
    });

})();
