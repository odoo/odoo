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
                var prettyfied = vkbeautify.xml(result[0].arch, "    ");
                var editingSession = new ace.EditSession(prettyfied + "\n");
                editingSession.setMode("ace/mode/xml");
                editingSession.setUndoManager(new ace.UndoManager());
                editor.setSession(editingSession);
            });
        },
        saveView: function () {
            openerp.jsonRpc('/web/dataset/call', 'call', {
                model: 'ir.ui.view',
                method: 'write',
                args: [[this.$viewList.val()], { 'arch': this.aceEditor.getValue() }]
            }).then(function(result) {
                window.location.reload();
            });
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
