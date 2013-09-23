(function () {
    'use strict';

    var website = openerp.website;
    website.templates.push('/website/static/src/xml/website.translator.xml');

    website.EditorBar.include({
        start: function () {
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                // TODO: refactor once xmo's feature branch is merged
                //       and make t-field's work as well as text translation
                self.$('button[data-action=edit]').text("Translate");
                self.$('[data-action=snippet]').hide();
                self.$('#customize-menu-button').hide();
            });
        },
        edit: function () {
            var self = this;
            if (!localStorage['website_translator_nodialog']) {
                var dialog = new website.TranslatorDialog();
                dialog.appendTo($(document.body));
                dialog.on('activate', this, function () {
                    dialog.$el.modal('hide');
                    this.translate();
                });
            } else {
                this.translate();
            }
        },
        translate: function () {
            var self = this;
            // this.edit();
            this.$('#website-top-view').hide();
            this.$('#website-top-edit').show();
            $('.css_non_editable_mode_hidden').removeClass("css_non_editable_mode_hidden");

            this.translations = null;
            openerp.jsonRpc('/website/get_view_translations', 'call', {
                'xml_id': $(document.documentElement).data('view-xmlid'),
                'context': website.get_context(),
            }).then(function (translations) {
                self.translations = translations;
                self.processTranslatableNodes();
            });
        },
        processTranslatableNodes: function () {
            var self = this;
            var $editables = $('[data-oe-model]')
                    .not('link, script')
                    .not('.oe_snippets,.oe_snippet, .oe_snippet *')
                    .not('[data-oe-type]');
            $editables.each(function () {
                self.transNode(this);
            });
            $('.oe_translatable_text').prop('contenteditable', true).on('paste', function () {
                var node = $(this);
                setTimeout(function () {
                    self.sanitizeNode(node);
                }, 0);
            });
            $(document).on('blur keyup paste', '.oe_translatable_text[contenteditable]', function(ev) {
                var $node = $(this);
                setTimeout(function () {
                    // Doing stuff next tick because past and keyup are
                    // fired before the content is changed
                    if (ev.type == 'paste') {
                        self.sanitizeNode($node[0]);
                    }
                    if ($node.data('initial_content') !== $node.text()) {
                        $node.addClass('oe_dirty').removeClass('oe_translatable_todo');
                    }
                }, 0);
            });
        },
        sanitizeNode: function (node) {
            node.text(node.text());
        },
        isTextNode: function (node) {
            return node.nodeType === 3 || node.nodeType === 4;
        },
        isTranslatable: function (text) {
            return text && _.str.trim(text) !== '';
        },
        markTranslatableNode: function (node) {
            // TODO: link nodes with same content
            node.className += ' oe_translatable_text oe_translatable_todo';
            node.contentEditable = true;
            $(node).data('initial_content', node.childNodes[0].data);
        },
        save: function () {
            var trans = {};
            // this._super.apply(this, arguments);
            $('.oe_translatable_text.oe_dirty').each(function () {
                var $node = $(this);
                var text = $node.text();
                var view_id = $(this).parents('[data-oe-model="ir.ui.view"]')
                                     .not('[data-oe-type]').first().data().oeId;
                if (!trans[view_id]) {
                    trans[view_id] = [];
                }
                trans[view_id].push({
                    initial_content: $node.data('initial_content'),
                    new_content: text
                });
            });
            openerp.jsonRpc('/website/set_translations', 'call', {
                'data': trans,
                'lang': website.get_context()['lang'],
            }).then(function () {
                website.reload();
            }).fail(function () {
                // TODO: bootstrap alert with error message
                alert("Could not save translation");
            });
        },
        transNode: function (node, context) {
            if (node.childNodes.length === 1
                    && this.isTextNode(node.childNodes[0])
                    && !node.getAttribute('data-oe-model')) {
                this.markTranslatableNode(node);
            } else {
                for (var i = 0, l = node.childNodes.length; i < l; i ++) {
                    var n = node.childNodes[i];
                    if (this.isTextNode(n)) {
                        if (this.isTranslatable(n.data)) {
                            var container = document.createElement('span');
                            node.insertBefore(container, n);
                            container.appendChild(n);
                            this.markTranslatableNode(container);
                        }
                    } else {
                        this.transNode(n);
                    }
                }
            }
        },
    });

    website.TranslatorDialog = openerp.Widget.extend({
        events: _.extend({}, website.EditorBar.prototype.events, {
            'hidden.bs.modal': 'destroy',
            'click button[data-action=activate]': function (ev) {
                this.trigger('activate');
            },
        }),
        template: 'website.TranslatorDialog',
        start: function () {
            this.$el.modal();
        },
    });
})();
