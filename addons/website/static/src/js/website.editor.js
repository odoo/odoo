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
    function image_dialog(editor) {
        return new website.editor.ImageDialog(editor).appendTo(document.body);
    }

    website.init_editor = function () {
        CKEDITOR.plugins.add('customdialogs', {
            requires: 'link,image',
            init: function (editor) {
                editor.on('doubleclick', function (evt) {
                    if (evt.data.dialog === 'link') {
                        delete evt.data.dialog;
                        link_dialog(editor);
                    } else if(evt.data.dialog === 'image') {
                        delete evt.data.dialog;
                        image_dialog(editor);
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
                        image_dialog(editor);
                        return true;
                    },
                    canUndo: false,
                    editorFocus: true,
                });
            }
        });
        CKEDITOR.plugins.add( 'tablebutton', {
            requires: 'panelbutton,floatpanel',
            init: function( editor ) {
                var label = "Table";

                editor.ui.add('TableButton', CKEDITOR.UI_PANELBUTTON, {
                    label: label,
                    title: label,
                    // use existing 'table' icon
                    icon: 'table',
                    modes: { wysiwyg: true },
                    editorFocus: true,
                    // panel opens in iframe, @css is CSS file <link>-ed within
                    // frame document, @attributes are set on iframe itself.
                    panel: {
                        css: '/website/static/src/css/editor.css',
                        attributes: { 'role': 'listbox', 'aria-label': label, },
                    },

                    onBlock: function (panel, block) {
                        block.autoSize = true;
                        block.element.setHtml(openerp.qweb.render('website.editor.table.panel', {
                            rows: 5,
                            cols: 5,
                        }));

                        var $table = $(block.element.$).on('mouseenter', 'td', function (e) {
                            var $e = $(e.target);
                            var y = $e.index() + 1;
                            var x = $e.closest('tr').index() + 1;

                            $table
                                .find('td').removeClass('selected').end()
                                .find('tr:lt(' + String(x) + ')')
                                .children().filter(function () { return $(this).index() < y; })
                                .addClass('selected');
                        }).on('click', 'td', function (e) {
                            var $e = $(e.target);

                            var table = new CKEDITOR.dom.element(
                                $(openerp.qweb.render('website.editor.table', {
                                    rows: $e.closest('tr').index() + 1,
                                    cols: $e.index() + 1,
                                }))[0]);

                            editor.insertElement(table);
                            setTimeout(function () {
                                var firstCell = new CKEDITOR.dom.element(table.$.rows[0].cells[0]);
                                var range = editor.createRange();
                                range.moveToPosition(firstCell, CKEDITOR.POSITION_AFTER_START);
                                range.select();
                            }, 0);
                        });

                        block.element.getDocument().getBody().setStyle('overflow', 'hidden');
                        CKEDITOR.ui.fire('ready', this);
                    },
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
                var view_id = $(event.currentTarget).data('view-id');
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
            var self = this;
            this.$buttons.edit.prop('disabled', true);
            this.$('#website-top-view').hide();
            this.$('#website-top-edit').show();
            $('.css_non_editable_mode_hidden').removeClass("css_non_editable_mode_hidden");

            var $editables = $('[data-oe-model]')
                    .not('link, script')
                    // FIXME: propagation should make "meta" blocks non-editable in the first place...
                    .not('.oe_snippets,.oe_snippet, .oe_snippet *')
                    .prop('contentEditable', true)
                    .addClass('oe_editable');
            var $rte_ables = $editables.not('[data-oe-type]');
            var $raw_editables = $editables.not($rte_ables);

            // temporary: on raw editables, links are still active so an
            // editable link, containing a link or within a link becomes very
            // hard to edit. Disable linking for these.
            $raw_editables.parents('a')
                .add($raw_editables.find('a'))
                .on('click', function (e) {
                    e.preventDefault();
                });

            this.rte.start_edition($rte_ables);
            $raw_editables.each(function () {
                observer.observe(this, OBSERVER_CONFIG);
            }).one('content_changed', function () {
                $(this).addClass('oe_dirty');
                self.rte_changed();
            });
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

        init: function (EditorBar) {
            this.EditorBar = EditorBar;
            this._super.apply(this, arguments);
        },

        start_edition: function ($elements) {
            var self = this;
            $elements
                .not('span, [data-oe-type]')
                .each(function () {
                    var node = this;
                    var $node = $(node);
                    var editor = CKEDITOR.inline(this, self._config());
                    editor.on('instanceReady', function () {
                        self.trigger('instanceReady');
                        observer.observe(node, OBSERVER_CONFIG);
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
                extraPlugins: 'sharedspace,customdialogs,tablebutton',
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
                        "Image", "TableButton"
                    ]},{
                    name: 'styles', items: [
                        "Styles"
                    ]}
                ],
                // styles dropdown in toolbar
                stylesSet: [
                    {name: "Normal", element: 'p'},
                    {name: "Heading 1", element: 'h1'},
                    {name: "Heading 2", element: 'h2'},
                    {name: "Heading 3", element: 'h3'},
                    {name: "Heading 4", element: 'h4'},
                    {name: "Heading 5", element: 'h5'},
                    {name: "Heading 6", element: 'h6'},
                    {name: "Formatted", element: 'pre'},
                    {name: "Address", element: 'address'},
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
            'hidden.bs.modal': 'destroy',
            'click button.save': 'save',
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
        save: function () {
            this.$el.modal('hide');
        },
    });

    website.editor.LinkDialog = website.editor.Dialog.extend({
        template: 'website.editor.dialog.link',
        events: _.extend({}, website.editor.Dialog.prototype.events, {
            'change .url-source': function (e) { this.changed($(e.target)); },
            'click div.existing a': 'select_page',
        }),
        init: function (editor) {
            this._super(editor);
            // url -> name mapping for existing pages
            this.pages = Object.create(null);
            // name -> url mapping for the same
            this.pages_by_name = Object.create(null);
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

                // focus dance between RTE & dialog blow up the stack in Safari
                // and Chrome, so defer select() until dialog has been closed
                setTimeout(function () {
                    range.select();
                }, 0);
            }
        },
        save: function () {
            var self = this, _super = this._super.bind(this);
            var $e = this.$('.url-source').filter(function () { return !!this.value; });

            var val = $e.val(), done = $.when();
            if ($e.hasClass('email-address')) {
                this.make_link('mailto:' + val, false, val);
            } else if ($e.hasClass('pages')) {
                // ``val`` is the *name* of the page
                var url = this.pages_by_name[val];
                if (!url) {
                    // Create the page, get the URL back
                    done = $.get(_.str.sprintf(
                        '/pagenew/%s?noredirect', encodeURIComponent(val)))
                        .then(function (response) {
                            url = response;
                        });
                }
                done.then(function () {
                    self.make_link(url, false, val);
                });
            } else {
                this.make_link(val, this.$('input.window-new').prop('checked'));
            }
            done.then(_super);
        },
        bind_data: function () {
            var href = this.element && (this.element.data( 'cke-saved-href')
                                    ||  this.element.getAttribute('href'));
            if (!href) { return; }

            var match, $control;
            if (match = /(mailto):(.+)/.exec(href)) {
                $control = this.$('input.email-address').val(match[2]);
            } else if(href in this.pages) {
                $control = this.$('input.pages').val(this.pages[href]);
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
         * Selected an existing page in dropdown
         */
        select_page: function (e) {
            e.preventDefault();
            e.stopPropagation();
            var $target = $(e.target);
            this.$('input.pages').val($target.text()).change();
            // No #dropdown('close'), and using #dropdown('toggle') sur
            // #closest('.dropdown') makes the dropdown not work correctly
            $target.closest('.open').removeClass('open');
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
            var $pages = this.$('div.existing ul').empty();
            _(results).each(function (result) {
                self.pages[result.url] = result.name;
                self.pages_by_name[result.name] = result.url;
                var $link = $('<a>').attr('href', result.url).text(result.name);
                $('<li>').append($link).appendTo($pages);
            });
        },
    });
    website.editor.ImageDialog = website.editor.Dialog.extend({
        template: 'website.editor.dialog.image',
        events: _.extend({}, website.editor.Dialog.prototype.events, {
            'change .url-source': function (e) { this.changed($(e.target)); },
            'click button.filepicker': function () {
                this.$('input[type=file]').click();
            },
            'change input[type=file]': 'file_selection',
            'change input.url': 'preview_image',
            'click .existing-attachments a': 'select_existing',
        }),
        start: function () {
            var selection = this.editor.getSelection();
            var el = selection && selection.getSelectedElement();
            this.element = null;
            if (el && el.is('img')) {
                this.element = el;
                this.set_image(el.getAttribute('src'));
            }

            return $.when(
                this._super(),
                this.fetch_existing().then(this.proxy('fetched_existing')));
        },
        save: function () {
            var url = this.$('input.url').val();
            var element, editor = this.editor;
            if (!(element = this.element)) {
                element = editor.document.createElement('img');
                // focus event handler interactions between bootstrap (modal)
                // and ckeditor (RTE) lead to blowing the stack in Safari and
                // Chrome (but not FF) when this is done synchronously =>
                // defer insertion so modal has been hidden & destroyed before
                // it happens
                setTimeout(function () {
                    editor.insertElement(element);
                }, 0);
            }
            element.setAttribute('src', url);
            this._super();
        },

        /**
         * Sets the provided image url as the dialog's value-to-save and
         * refreshes the preview element to use it.
         */
        set_image: function (url) {
            this.$('input.url').val(url);
            this.preview_image();
        },

        file_selection: function (e) {
            this.$('button.filepicker').removeClass('btn-danger btn-success');

            var self = this;
            var callback = _.uniqueId('func_');
            this.$('input[name=func]').val(callback);

            window[callback] = function (url, error) {
                delete window[callback];
                self.file_selected(url, error);
            };
            this.$('form').submit();
        },
        file_selected: function(url, error) {
            var $button = this.$('button.filepicker');
            if (error) {
                $button.addClass('btn-danger');
                return;
            }
            $button.addClass('btn-success');
            this.set_image(url);
        },
        preview_image: function () {
            var image = this.$('input.url').val();
            if (!image) { return; }

            this.$('img.image-preview').attr('src', image);
        },

        fetch_existing: function () {
            // FIXME: lazy load attachments?
            return openerp.jsonRpc('/web/dataset/call_kw', 'call', {
                model: 'ir.attachment',
                method: 'search_read',
                args: [],
                kwargs: {
                    fields: ['name'],
                    domain: [['res_model', '=', 'ir.ui.view']],
                    order: 'name',
                }
            });
        },
        fetched_existing: function (records) {
            // Create rows of 3 records
            var rows = _(records).chain()
                .groupBy(function (_, index) { return Math.floor(index / 3); })
                .values()
                .value();
            this.$('.existing-attachments').replaceWith(
                openerp.qweb.render('website.editor.dialog.image.existing', {rows: rows}));
        },
        select_existing: function (e) {
            e.preventDefault();
            this.set_image(e.currentTarget.getAttribute('href'));
        },
    });


    var Observer = window.MutationObserver || window.WebkitMutationObserver || window.JsMutationObserver;
    var OBSERVER_CONFIG = {
        childList: true,
        attributes: true,
        characterData: true,
        subtree: true,
        attributeOldValue: true,
    };
    var observer = new Observer(function (mutations) {
        // NOTE: Webkit does not fire DOMAttrModified => webkit browsers
        //       relying on JsMutationObserver shim (Chrome < 18, Safari < 6)
        //       will not mark dirty on attribute changes (@class, img/@src,
        //       a/@href, ...)
        _(mutations).chain()
                .filter(function (m) {
                switch(m.type) {
                case 'attributes': // ignore .cke_focus being added or removed
                    // if attribute is not a class, can't be .cke_focus change
                    if (m.attributeName !== 'class') { return true; }

                    // find out what classes were added or removed
                    var oldClasses = m.oldValue.split(/\s+/);
                    var newClasses = m.target.className.split(/\s+/);
                    var change = _.union(_.difference(oldClasses, newClasses),
                                         _.difference(newClasses, oldClasses));
                    // ignore mutation if the *only* change is .cke_focus
                    return change.length !== 1 || change[0] === 'cke_focus';
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
