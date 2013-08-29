(function () {
    'use strict';

    var website = openerp.website;

    website.templates.push('/website/static/src/xml/website.editor.xml');
    website.dom_ready.done(function () {
        // $.fn.data automatically parses value, '0'|'1' -> 0|1
        website.is_editable = $(document.documentElement).data('editable');
        var is_smartphone = $(document.body)[0].clientWidth < 767;

        if (website.is_editable && !is_smartphone) {
            website.ready().then(website.init_editor);
        }
    });

    function link_dialog(editor) {
        return new website.editor.LinkDialog(editor).appendTo(document.body);
    }

    website.init_editor = function () {
        CKEDITOR.plugins.add('customdialogs', {
            requires: 'link,image',
            init: function (editor) {
                editor.on('doubleclick', function (evt) {
                    if (evt.data.dialog === 'link' || evt.data.dialog === 'image') {
                        delete evt.data.dialog;
                        link_dialog(editor);
                    }
                    // priority should be smaller than dialog (999) but bigger
                    // than link or image (default=10)
                }, null, null, 500);

                editor.addCommand('link', {
                    exec: function (editor, data) {
                        link_dialog(editor);
                        return true;
                    },
                    canUndo: false,
                    editorFocus: true,
                });
                editor.addCommand('image', {
                    exec: function (editor, data) {
                        console.log('image', editor, data);
                        return true;
                    },
                    canUndo: false,
                    editorFocus: true,
                });

            }
        });
        var editor = new website.EditorBar();
        var $body = $(document.body);
        editor.prependTo($body);
        $body.css('padding-top', '50px'); // Not working properly: editor.$el.outerHeight());
    };
        /* ----- TOP EDITOR BAR FOR ADMIN ---- */
    website.EditorBar = openerp.Widget.extend({
        template: 'website.editorbar',
        events: {
            'click button[data-action=edit]': 'edit',
            'click button[data-action=save]': 'save',
            'click button[data-action=cancel]': 'cancel',
        },
        container: 'body',
        customize_setup: function() {
            var self = this;
            var view_name = $(document.documentElement).data('view-xmlid');
            var menu = $('#customize-menu');
            this.$('#customize-menu-button').click(function(event) {
                menu.empty();
                openerp.jsonRpc('/website/customize_template_get', 'call', { 'xml_id': view_name }).then(
                    function(result) {
                        _.each(result, function (item) {
                            if (item.header) {
                                menu.append('<li class="dropdown-header">' + item.name + '</li>');
                            } else {
                                menu.append(_.str.sprintf('<li role="presentation"><a href="#" data-view-id="%s" role="menuitem"><strong class="icon-check%s"></strong> %s</a></li>',
                                    item.id, item.active ? '' : '-empty', item.name));
                            }
                        });
                        // Adding Static Menus
                        menu.append('<li class="divider"></li><li><a href="/page/website.themes">Change Theme</a></li>');
                    }
                );
            });
            menu.on('click', 'a', function (event) {
                var view_id = $(event.target).data('view-id');
                openerp.jsonRpc('/website/customize_template_toggle', 'call', {
                    'view_id': view_id
                }).then( function(result) {
                    window.location.reload();
                });
            });
        },
        start: function() {
            var self = this;

            this.saving_mutex = new openerp.Mutex();

            this.$('#website-top-edit').hide();
            this.$('#website-top-view').show();

            $('.dropdown-toggle').dropdown();
            this.customize_setup();

            this.$buttons = {
                edit: this.$('button[data-action=edit]'),
                save: this.$('button[data-action=save]'),
                cancel: this.$('button[data-action=cancel]'),
            };

            this.rte = new website.RTE(this);
            this.rte.on('change', this, this.proxy('rte_changed'));

            return $.when(
                this._super.apply(this, arguments),
                this.rte.prependTo(this.$('#website-top-edit .nav.pull-right'))
            );
        },
        edit: function () {
            this.$buttons.edit.prop('disabled', true);
            this.$('#website-top-view').hide();
            this.$('#website-top-edit').show();

            // this.$buttons.cancel.add(this.$buttons.snippet).prop('disabled', false)
            //     .add(this.$buttons.save)
            //     .parent().show();
            //
            // TODO: span edition changing edition state (save button)
            var $editables = $('[data-oe-model]')
                    .not('link, script')
                    // FIXME: propagation should make "meta" blocks non-editable in the first place...
                    .not('.oe_snippets,.oe_snippet, .oe_snippet *')
                    .prop('contentEditable', true)
                    .addClass('oe_editable');
            var $rte_ables = $editables.not('[data-oe-type]');
            var $raw_editables = $editables.not($rte_ables);

            // temporary fix until we fix ckeditor
            $raw_editables.each(function () {
                $(this).parents().add($(this).find('*')).on('click', function(ev) {
                    ev.preventDefault();
                    ev.stopPropagation();
                });
            });

            this.rte.start_edition($rte_ables);
            $raw_editables.on('keydown keypress cut paste', function (e) {
                var $target = $(e.target);
                if ($target.hasClass('oe_dirty')) {
                    return;
                }

                $target.addClass('oe_dirty');
                this.$buttons.save.prop('disabled', false);
            }.bind(this));
        },
        rte_changed: function () {
            this.$buttons.save.prop('disabled', false);
        },
        save: function () {
            var self = this;
            var defs = [];
            observer.disconnect();
            $('.oe_dirty').each(function (i, v) {
                var $el = $(this);
                // TODO: Add a queue with concurrency limit in webclient
                // https://github.com/medikoo/deferred/blob/master/lib/ext/function/gate.js
                var def = self.saving_mutex.exec(function () {
                    return self.saveElement($el).then(function () {
                        $el.removeClass('oe_dirty');
                    }).fail(function () {
                        var data = $el.data();
                        console.error(_.str.sprintf('Could not save %s#%d#%s', data.oeModel, data.oeId, data.oeField));
                    });
                });
                defs.push(def);
            });
            return $.when.apply(null, defs).then(function () {
                window.location.reload();
            });
        },
        saveElement: function ($el) {
            var data = $el.data();
            var html = $el.html();
            var xpath = data.oeXpath;
            if (xpath) {
                var $w = $el.clone();
                $w.removeClass('oe_dirty');
                _.each(['model', 'id', 'field', 'xpath'], function(d) {$w.removeAttr('data-oe-' + d);});
                $w
                    .removeClass('oe_editable')
                    .prop('contentEditable', false);
                html = $w.wrap('<div>').parent().html();
            }
            return openerp.jsonRpc('/web/dataset/call', 'call', {
                model: 'ir.ui.view',
                method: 'save',
                args: [data.oeModel, data.oeId, data.oeField, html, xpath]
            });
        },
        cancel: function () {
            window.location.reload();
        },
    });

    /* ----- RICH TEXT EDITOR ---- */
    website.RTE = openerp.Widget.extend({
        tagName: 'li',
        id: 'oe_rte_toolbar',
        className: 'oe_right oe_rte_toolbar',
        // editor.ui.items -> possible commands &al
        // editor.applyStyle(new CKEDITOR.style({element: "span",styles: {color: "#(color)"},overrides: [{element: "font",attributes: {color: null}}]}, {color: '#ff0000'}));

        start_edition: function ($elements) {
            var self = this;
            $elements
                .not('span, [data-oe-type]')
                .each(function () {
                    var node = this;
                    var $node = $(node);
                    var editor = CKEDITOR.inline(this, self._config());
                    editor.on('instanceReady', function () {
                        observer.observe(node, {
                            childList: true,
                            attributes: true,
                            characterData: true,
                            subtree: true
                        });
                    });
                    $node.one('content_changed', function () {
                        $node.addClass('oe_dirty');
                        self.trigger('change');
                    });
                });
        },

        _current_editor: function () {
            return CKEDITOR.currentInstance;
        },
        _config: function () {
            var removed_plugins = [
                    // remove custom context menu
                    'contextmenu,tabletools,liststyle',
                    // magicline captures mousein/mouseout => draggable does not work
                    'magicline'
            ];
            return {
                // Disable auto-generated titles
                // FIXME: accessibility, need to generate user-sensible title, used for @title and @aria-label
                title: false,
                removePlugins: removed_plugins.join(','),
                uiColor: '',
                // Ensure no config file is loaded
                customConfig: '',
                // Disable ACF
                allowedContent: true,
                // Don't insert paragraphs around content in e.g. <li>
                autoParagraph: false,
                filebrowserImageUploadUrl: "/website/attach",
                // Support for sharedSpaces in 4.x
                extraPlugins: 'sharedspace,customdialogs',
                // Place toolbar in controlled location
                sharedSpaces: { top: 'oe_rte_toolbar' },
                toolbar: [
                    {name: 'basicstyles', items: [
                        "Bold", "Italic", "Underline", "Strike", "Subscript",
                        "Superscript", "TextColor", "BGColor", "RemoveFormat"
                    ]},{
                    name: 'span', items: [
                        "Link", "Unlink", "Blockquote", "BulletedList",
                        "NumberedList", "Indent", "Outdent"
                    ]},{
                    name: 'justify', items: [
                        "JustifyLeft", "JustifyCenter", "JustifyRight", "JustifyBlock"
                    ]},{
                    name: 'special', items: [
                        "Image", "Table"
                    ]},{
                    name: 'styles', items: [
                        "Format", "Styles"
                    ]}
                ],
                // styles dropdown in toolbar
                stylesSet: [
                    // emphasis
                    {name: "Muted", element: 'span', attributes: {'class': 'text-muted'}},
                    {name: "Primary", element: 'span', attributes: {'class': 'text-primary'}},
                    {name: "Warning", element: 'span', attributes: {'class': 'text-warning'}},
                    {name: "Danger", element: 'span', attributes: {'class': 'text-danger'}},
                    {name: "Success", element: 'span', attributes: {'class': 'text-success'}},
                    {name: "Info", element: 'span', attributes: {'class': 'text-info'}}
                ],
            };
        },
    });

    website.editor = { };
    website.editor.Dialog = openerp.Widget.extend({
        events: {
            'hidden': 'destroy',
        },
        init: function (editor) {
            this._super();
            this.editor = editor;
        },
        start: function () {
            var sup = this._super();
            this.$el.modal();
            return sup;
        },
    });

    website.editor.LinkDialog = website.editor.Dialog.extend({
        template: 'website.editor.dialog.link',
        events: _.extend({}, website.editor.Dialog.prototype.events, {
            'click button.btn-primary': 'save',
            'change .url-source': function (e) { this.changed($(e.target)); },
        }),
        init: function (editor) {
            this._super(editor);
            this.pages = Object.create(null);
        },
        start: function () {
            var element;
            if ((element = this.get_selected_link()) && element.hasAttribute('href')) {
                this.editor.getSelection().selectElement(element);
            }
            this.element = element;

            return $.when(
                this.fetch_pages().done(this.proxy('fill_pages')),
                this._super()
            ).done(this.proxy('bind_data'));
        },
        /**
         * Greatly simplified version of CKEDITOR's
         * plugins.link.dialogs.link.onOk.
         *
         * @param {String} url
         * @param {Boolean} [new_window=false]
         * @param {String} [label=null]
         */
        make_link: function (url, new_window, label) {
            var attributes = {href: url, 'data-cke-saved-href': url};
            var to_remove = [];
            if (new_window) {
                attributes['target'] = '_blank';
            } else {
                to_remove.push('target');
            }

            if (this.element) {
                this.element.setAttributes(attributes);
                this.element.removeAttributes(to_remove);
            } else {
                var selection = this.editor.getSelection();
                var range = selection.getRanges(true)[0];

                if (range.collapsed) {
                    var text = new CKEDITOR.dom.text(label || url);
                    range.insertNode(text);
                    range.selectNodeContents(text);
                }

                new CKEDITOR.style({
                    type: CKEDITOR.STYLE_INLINE,
                    element: 'a',
                    attributes: attributes,
                }).applyToRange(range);
                // blows up the call stack, not sure why as original version
                // seems to work OK
                // range.select();
            }
        },
        save: function () {
            var $e = this.$('.url-source').filter(function () { return !!this.value; });

            var val = $e.val();
            if ($e.hasClass('email-address')) {
                this.make_link('mailto:' + val, false, val);
            } else if ($e.hasClass('pages')) {
                this.make_link(val, false, $e.find('option:selected').text());
            } else {
                this.make_link(val, this.$('input.window-new').prop('checked'));
            }
            this.$el.modal('hide');
        },
        bind_data: function () {
            var href = this.element && (this.element.data( 'cke-saved-href')
                                    ||  this.element.getAttribute('href'));
            if (!href) { return; }

            var match, $control;
            if (match = /(mailto):(.+)/.exec(href)) {
                $control = this.$('input.email-address').val(match[2]);
            } else if(href in this.pages) {
                $control = this.$('select.pages').val(href);
            }
            if (!$control) {
                $control = this.$('input.url').val(href);
            }

            this.changed($control);

            this.$('input.window-new').prop(
                'checked', this.element.getAttribute('target') === '_blank');
        },
        changed: function ($e) {
            $e.closest('li.list-group-item').addClass('active')
              .siblings().removeClass('active');
            this.$('.url-source').not($e).val('');
        },
        /**
         * CKEDITOR.plugins.link.getSelectedLink ignores the editor's root,
         * if the editor is set directly on a link it will thus not work.
         */
        get_selected_link: function () {
            var sel = this.editor.getSelection(),
                el = sel.getSelectedElement();
            if (el && el.is('a')) { return el; }

            var range = sel.getRanges(true)[0];
            if (!range) { return null; }

            range.shrink(CKEDITOR.SHRINK_TEXT);
            return this.editor.elementPath(range.getCommonAncestor())
                              .contains('a');

        },
        fetch_pages: function () {
            return openerp.jsonRpc('/web/dataset/call_kw', 'call', {
                model: 'website',
                method: 'list_pages',
                args: [],
                kwargs: {}
            });
        },
        fill_pages: function (results) {
            var self = this;
            var $select = this.$('select');
            $select.append(new Option());
            _(results).each(function (result) {
                self.pages[result.url] = true;
                $select.append(new Option(result.name, result.url));
            });
        },
    });


    var Observer = window.MutationObserver || window.WebkitMutationObserver || window.JsMutationObserver;
    var observer = new Observer(function (mutations) {
        _(mutations).chain()
            .filter(function (m) {
                switch(m.type) {
                case 'attributes':
                    // ignore cke_focus being added & removed from RTE root
                    // FIXME: what if snippets are configured by adding/removing classes on their root element?
                    return !$(m.target).hasClass('oe_editable');
                case 'childList':
                    // <br type="_moz"> appears when focusing RTE in FF, ignore
                    return m.addedNodes.length !== 1 || m.addedNodes[0].nodeName !== 'BR';
                default:
                    return true;
                }
            })
            .map(function (m) {
                var node = m.target;
                while (node && !$(node).hasClass('oe_editable')) {
                    node = node.parentNode;
                }
                return node;
            })
            .compact()
            .uniq()
            .each(function (node) { $(node).trigger('content_changed'); })
    });
})();
