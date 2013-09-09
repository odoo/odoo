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
            }
            editor.show();
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
            'click button[data-action=save-view]': 'saveView',
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
                    editor.getSession().setMode("ace/mode/xml");
                    self.aceEditor = editor;
                    self.displayView();
                });
        },
        displayView: function () {
            var self = this;
            var viewId = self.$viewList.val();
            openerp.jsonRpc('/web/dataset/call', 'call', {
                model: 'ir.ui.view',
                method: 'read',
                args: [[viewId], ['arch']]
            }).then(function(result) {
                var viewXML = result[0].arch;
                self.aceEditor.setValue(viewXML);
                self.aceEditor.clearSelection();
                self.aceEditor.navigateTo(0, 0);
            });
        },
        saveView: function () {
            var self = this;
            var viewId = self.$viewList.val();
            var viewXML = self.aceEditor.getValue();
            openerp.jsonRpc('/web/dataset/call', 'call', {
                model: 'ir.ui.view',
                method: 'write',
                args: [[viewId], { 'arch': viewId }]
            }).then(function(result) {
                window.location.reload();
            });
        },
        hide: function () {
            // TODO Finish
        },
        show: function () {
            // TODO Finish
        },
        destroy: function () {
            editor = null;
            this._super();
        },
    });

})();
