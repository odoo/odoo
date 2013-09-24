(function () {
    'use strict';

    var website = openerp.website;
    // $.fn.data automatically parses value, '0'|'1' -> 0|1
    website.is_editable = $(document.documentElement).data('editable');

    website.templates.push('/website/static/src/xml/website.editor.xml');
    website.dom_ready.done(function () {
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

    if (website.is_editable) {
        // only enable editors manually
        CKEDITOR.disableAutoInline = true;
        // EDIT ALL THE THINGS
        CKEDITOR.dtd.$editable = $.extend(
            {}, CKEDITOR.dtd.$block, CKEDITOR.dtd.$inline);
        // Disable removal of empty elements on CKEDITOR activation. Empty
        // elements are used for e.g. support of FontAwesome icons
        CKEDITOR.dtd.$removeEmpty = {};
    }
    website.init_editor = function () {
        CKEDITOR.plugins.add('customdialogs', {
//            requires: 'link,image',
            init: function (editor) {
                editor.on('doubleclick', function (evt) {
                    var element = evt.data.element;
                    if (element.is('img')
                            && !element.data('cke-realelement')
                            && !element.isReadOnly()
                            && (element.data('oe-model') !== 'ir.ui.view')) {
                        image_dialog(editor);
                        return;
                    }

                    element = get_selected_link(editor) || evt.data.element;
                    if (element.isReadOnly()
                        || !element.is('a')
                        || element.data('oe-model')) {
                        return;
                    }

                    editor.getSelection().selectElement(element);
                    link_dialog(editor);
                }, null, null, 500);

                //noinspection JSValidateTypes
                editor.addCommand('link', {
                    exec: function (editor, data) {
                        link_dialog(editor);
                        return true;
                    },
                    canUndo: false,
                    editorFocus: true,
                });
                //noinspection JSValidateTypes
                editor.addCommand('image', {
                    exec: function (editor, data) {
                        image_dialog(editor);
                        return true;
                    },
                    canUndo: false,
                    editorFocus: true,
                });

                editor.ui.addButton('Link', {
                    label: 'Link',
                    command: 'link',
                    toolbar: 'links,10',
                    icon: '/website/static/lib/ckeditor/plugins/link/icons/link.png',
                });
                editor.ui.addButton('Image', {
                    label: 'Image',
                    command: 'image',
                    toolbar: 'insert,10',
                    icon: '/website/static/lib/ckeditor/plugins/image/icons/image.png',
                });

                editor.setKeystroke(CKEDITOR.CTRL + 76 /*L*/, 'link');
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

                            //noinspection JSPotentiallyInvalidConstructorUsage
                            var table = new CKEDITOR.dom.element(
                                $(openerp.qweb.render('website.editor.table', {
                                    rows: $e.closest('tr').index() + 1,
                                    cols: $e.index() + 1,
                                }))[0]);

                            editor.insertElement(table);
                            setTimeout(function () {
                                //noinspection JSPotentiallyInvalidConstructorUsage
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

        CKEDITOR.plugins.add('oeref', {
            requires: 'widget',

            init: function (editor) {
                editor.widgets.add('oeref', {
                    editables: { text: '*' },

                    upcast: function (el) {
                        return el.attributes['data-oe-type'];
                    },
                });
            }
        });

        var editor = new website.EditorBar();
        var $body = $(document.body);
        editor.prependTo($body).then(function () {
            if (location.search.indexOf("unable_editor") >= 0) {
                editor.edit();
            }
        });
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
                        menu.append('<li class="divider"></li><li><a data-action="ace" href="#">Advanced view editor</a></li>');
                    }
                );
            });
            menu.on('click', 'a[data-action!=ace]', function (event) {
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
            this.rte.on('rte:ready', this, function () {
                self.trigger('rte:ready');
            });

            return $.when(
                this._super.apply(this, arguments),
                this.rte.appendTo(this.$('#website-top-edit .nav.pull-right'))
            );
        },
        edit: function () {
            var self = this;
            this.$buttons.edit.prop('disabled', true);
            this.$('#website-top-view').hide();
            this.$('#website-top-edit').show();
            $('.css_non_editable_mode_hidden').removeClass("css_non_editable_mode_hidden");

            this.rte.start_edition();
        },
        rte_changed: function () {
            this.$buttons.save.prop('disabled', false);
        },
        save: function () {
            var self = this;

            observer.disconnect();
            var editor = this.rte.editor;
            var root = editor.element.$;
            editor.destroy();
            // FIXME: select editables then filter by dirty?
            var defs = this.rte.fetch_editables(root)
                .removeClass('oe_editable cke_focus')
                .removeAttr('contentEditable')
                .filter('.oe_dirty')
                .map(function () {
                    var $el = $(this);
                    // TODO: Add a queue with concurrency limit in webclient
                    // https://github.com/medikoo/deferred/blob/master/lib/ext/function/gate.js
                    return self.saving_mutex.exec(function () {
                        return self.saveElement($el)
                            .fail(function () {
                                var data = $el.data();
                                console.error(_.str.sprintf('Could not save %s(%d).%s', data.oeModel, data.oeId, data.oeField));
                            });
                    });
                }).get();
            return $.when.apply(null, defs).then(function () {
                window.location.href = window.location.href.replace(/unable_editor(=[^&]*)?|#.*/g, '');
            });
        },
        /**
         * Saves an RTE content, which always corresponds to a view section (?).
         */
        saveElement: function ($el) {
            $el.removeClass('oe_dirty');
            var markup = $el.prop('outerHTML');
            return openerp.jsonRpc('/web/dataset/call', 'call', {
                model: 'ir.ui.view',
                method: 'save',
                args: [$el.data('oe-id'), markup,
                       $el.data('oe-xpath') || null,
                       website.get_context()],
            });
        },
        cancel: function () {
            window.location.href = window.location.href.replace(/unable_editor(=[^&]*)?|#.*/g, '');
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
            // create a single editor for the whole page
            var root = document.getElementById('wrapwrap');
            $(root).attr('data-cke-editable', 'true')
                    .on('dragstart', 'img', function (e) {
                        e.preventDefault();
                    });
            this.editor = CKEDITOR.inline(root, self._config());
            this.editor.on('instanceReady', function () {
                // ckeditor set root to editable, disable it (only inner
                // sections are editable)
                // FIXME: are there cases where the whole editor is editable?
                root.contentEditable = false;

                self.setup_editables(root);

                self.trigger('rte:ready');
            });
        },

        setup_editables: function (root) {
            // selection of editable sub-items was previously in
            // EditorBar#edit, but for some unknown reason the elements were
            // apparently removed and recreated (?) at editor initalization,
            // and observer setup was lost.
            var self = this;
            // setup dirty-marking for each editable element
            this.fetch_editables(root)
                .prop('contentEditable', true)
                .addClass('oe_editable')
                .each(function () {
                    var node = this;
                    observer.observe(node, OBSERVER_CONFIG);
                    var $node = $(node);
                    $node.one('content_changed', function () {
                        $node.addClass('oe_dirty');
                        self.trigger('change');
                    });
                });
        },

        fetch_editables: function (root) {
            return $(root).find('[data-oe-model]')
                // FIXME: propagation should make "meta" blocks non-editable in the first place...
                .not('link, script')
                .not('.oe_snippet_editor')
                .filter(function () {
                    var $this = $(this);
                    // keep view sections and fields which are *not* in
                    // view sections for toplevel editables
                    return $this.data('oe-model') === 'ir.ui.view'
                       || !$this.closest('[data-oe-model = "ir.ui.view"]').length;
                });
        },

        _current_editor: function () {
            return CKEDITOR.currentInstance;
        },
        _config: function () {
            // base plugins minus
            // - magicline (captures mousein/mouseout -> breaks draggable)
            // - contextmenu & tabletools (disable contextual menu)
            // - bunch of unused plugins
            var plugins = [
                'a11yhelp', 'basicstyles', 'bidi', 'blockquote',
                'clipboard', 'colorbutton', 'colordialog', 'dialogadvtab',
                'elementspath', 'enterkey', 'entities', 'filebrowser',
                'find', 'floatingspace','format', 'htmlwriter', 'iframe',
                'indentblock', 'indentlist', 'justify',
                'list', 'pastefromword', 'pastetext', 'preview',
                'removeformat', 'resize', 'save', 'selectall', 'stylescombo',
                'tab', 'table', 'templates', 'toolbar', 'undo', 'wysiwygarea'
            ];
            return {
                // FIXME
                language: 'en',
                // Disable auto-generated titles
                // FIXME: accessibility, need to generate user-sensible title, used for @title and @aria-label
                title: false,
                plugins: plugins.join(','),
                uiColor: '',
                // FIXME: currently breaks RTE?
                // Ensure no config file is loaded
                customConfig: '',
                // Disable ACF
                allowedContent: true,
                // Don't insert paragraphs around content in e.g. <li>
                autoParagraph: false,
                // Don't automatically add &nbsp; or <br> in empty block-level
                // elements when edition starts
                fillEmptyBlocks: false,
                filebrowserImageUploadUrl: "/website/attach",
                // Support for sharedSpaces in 4.x
                extraPlugins: 'sharedspace,customdialogs,tablebutton,oeref',
                // Place toolbar in controlled location
                sharedSpaces: { top: 'oe_rte_toolbar' },
                toolbar: [{
                    name: 'clipboard', items: [
                        "Undo"
                    ]},{
                        name: 'basicstyles', items: [
                        "Bold", "Italic", "Underline", "Strike", "Subscript",
                        "Superscript", "TextColor", "BGColor", "RemoveFormat"
                    ]},{
                    name: 'span', items: [
                        "Link", "Blockquote", "BulletedList",
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
            this.close();
        },
        close: function () {
            this.$el.modal('hide');
        },
    });

    website.editor.LinkDialog = website.editor.Dialog.extend({
        template: 'website.editor.dialog.link',
        events: _.extend({}, website.editor.Dialog.prototype.events, {
            'change .url-source': function (e) { this.changed($(e.target)); },
            'mousedown': function (e) {
                var $target = $(e.target).closest('.list-group-item');
                if (!$target.length || $target.hasClass('active')) {
                    // clicked outside groups, or clicked in active groups
                    return;
                }

                this.changed($target.find('.url-source'));
            },
            'click button.remove': 'remove_link',
        }),
        init: function (editor) {
            this._super(editor);
            // url -> name mapping for existing pages
            this.pages = Object.create(null);
        },
        start: function () {
            var element;
            if ((element = this.get_selected_link()) && element.hasAttribute('href')) {
                this.editor.getSelection().selectElement(element);
            }
            this.element = element;
            if (element) {
                this.add_removal_button();
            }

            return $.when(
                this.fetch_pages().done(this.proxy('fill_pages')),
                this._super()
            ).done(this.proxy('bind_data'));
        },
        add_removal_button: function () {
            this.$('.modal-footer').prepend(
                openerp.qweb.render(
                    'website.editor.dialog.link.footer-button'));
        },
        remove_link: function () {
            var editor = this.editor;
            // same issue as in make_link
            setTimeout(function () {
                editor.removeStyle(new CKEDITOR.style({
                    element: 'a',
                    type: CKEDITOR.STYLE_INLINE,
                    alwaysRemoveElement: true,
                }));
            }, 0);
            this.close();
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
                    //noinspection JSPotentiallyInvalidConstructorUsage
                    var text = new CKEDITOR.dom.text(label || url);
                    range.insertNode(text);
                    range.selectNodeContents(text);
                }

                //noinspection JSPotentiallyInvalidConstructorUsage
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
            var $e = this.$('.list-group-item.active .url-source');
            var val = $e.val();
            if (!val || !$e[0].checkValidity()) {
                // FIXME: error message
                $e.closest('.form-group').addClass('has-error');
                return;
            }

            var done = $.when();
            if ($e.hasClass('email-address')) {
                this.make_link('mailto:' + val, false, val);
            } else if ($e.hasClass('existing')) {
                self.make_link(val, false, this.pages[val]);
            } else if ($e.hasClass('pages')) {
                // Create the page, get the URL back
                done = $.get(_.str.sprintf(
                        '/pagenew/%s?noredirect', encodeURIComponent(val)))
                    .then(function (response) {
                        self.make_link(response, false, val);
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
            if (match = /mailto:(.+)/.exec(href)) {
                $control = this.$('input.email-address').val(match[1]);
            } else if (href in this.pages) {
                $control = this.$('select.existing').val(href);
            } else if (match = /\/page\/(.+)/.exec(href)) {
                var actual_href = '/page/website.' + match[1];
                if (actual_href in this.pages) {
                    $control = this.$('select.existing').val(actual_href);
                }
            }
            if (!$control) {
                $control = this.$('input.url').val(href);
            }

            this.changed($control);

            this.$('input.window-new').prop(
                'checked', this.element.getAttribute('target') === '_blank');
        },
        changed: function ($e) {
            this.$('.url-source').not($e).val('');
            $e.closest('.list-group-item')
                .addClass('active')
                .siblings().removeClass('active')
                .addBack().removeClass('has-error');
        },
        /**
         * CKEDITOR.plugins.link.getSelectedLink ignores the editor's root,
         * if the editor is set directly on a link it will thus not work.
         */
        get_selected_link: function () {
            return get_selected_link(this.editor);
        },
        fetch_pages: function () {
            return openerp.jsonRpc('/web/dataset/call_kw', 'call', {
                model: 'website',
                method: 'list_pages',
                args: [null],
                kwargs: {
                    context: website.get_context()
                },
            });
        },
        fill_pages: function (results) {
            var self = this;
            var pages = this.$('select.existing')[0];
            _(results).each(function (result) {
                self.pages[result.url] = result.name;

                pages.options[pages.options.length] =
                        new Option(result.name, result.url);
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
            'click a[href=#existing]': 'browse_existing',
            'change select.image-style': 'preview_image',
        }),
        start: function () {
            var selection = this.editor.getSelection();
            var el = selection && selection.getSelectedElement();
            this.element = null;

            var $select = this.$('.image-style');
            var $options = $select.children();
            this.image_styles = $options.map(function () { return this.value; }).get();

            if (el && el.is('img')) {
                this.element = el;
                _(this.image_styles).each(function (style) {
                    if (el.hasClass(style)) {
                        $select.val(style);
                    }
                });
                // set_image must follow setup of image style
                this.set_image(el.getAttribute('src'));
            }

            return this._super();
        },
        save: function () {
            var url = this.$('input.url').val();
            var style = this.$('.image-style').val();
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
            $(element.$).removeClass(this.image_styles.join(' '));
            if (style) { element.addClass(style); }

            return this._super();
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

            this.$('img.image-preview')
                .attr('src', image)
                .removeClass(this.image_styles.join(' '))
                .addClass(this.$('select.image-style').val());
        },

        browse_existing: function (e) {
            e.preventDefault();
            new website.editor.ExistingImageDialog(this).appendTo(document.body);
        },
    });

    var IMAGES_PER_ROW = 6;
    var IMAGES_ROWS = 4;
    website.editor.ExistingImageDialog = website.editor.Dialog.extend({
        template: 'website.editor.dialog.image.existing',
        events: _.extend({}, website.editor.Dialog.prototype.events, {
            'click .existing-attachments img': 'select_existing',
            'click .pager > li': function (e) {
                e.preventDefault();
                var $target = $(e.currentTarget);
                if ($target.hasClass('disabled')) {
                    return;
                }
                this.page += $target.hasClass('previous') ? -1 : 1;
                this.display_attachments();
            },
        }),
        init: function (parent) {
            this.image = null;
            this.page = 0;
            this.parent = parent;
            this._super(parent.editor);
        },

        start: function () {
            return $.when(
                this._super(),
                this.fetch_existing().then(this.proxy('fetched_existing')));
        },

        fetch_existing: function () {
            return openerp.jsonRpc('/web/dataset/call_kw', 'call', {
                model: 'ir.attachment',
                method: 'search_read',
                args: [],
                kwargs: {
                    fields: ['name', 'website_url'],
                    domain: [['res_model', '=', 'ir.ui.view']],
                    order: 'name',
                    context: website.get_context(),
                }
            });
        },
        fetched_existing: function (records) {
            this.records = records;
            this.display_attachments();
        },
        display_attachments: function () {
            var per_screen = IMAGES_PER_ROW * IMAGES_ROWS;

            var from = this.page * per_screen;
            var records = this.records;

            // Create rows of 3 records
            var rows = _(records).chain()
                .slice(from, from + per_screen)
                .groupBy(function (_, index) { return Math.floor(index / IMAGES_PER_ROW); })
                .values()
                .value();

            this.$('.existing-attachments').replaceWith(
                openerp.qweb.render(
                    'website.editor.dialog.image.existing.content', {rows: rows}));
            this.$('.pager')
                .find('li.previous').toggleClass('disabled', (from === 0)).end()
                .find('li.next').toggleClass('disabled', (from + per_screen >= records.length));

        },
        select_existing: function (e) {
            var link = $(e.currentTarget).attr('src');
            if (link) {
                this.parent.set_image(link);
            }
            this.close()
        },
    });

    function get_selected_link(editor) {
        var sel = editor.getSelection(),
            el = sel.getSelectedElement();
        if (el && el.is('a')) { return el; }

        var range = sel.getRanges(true)[0];
        if (!range) { return null; }

        range.shrink(CKEDITOR.SHRINK_TEXT);
        var commonAncestor = range.getCommonAncestor();
        var viewRoot = editor.elementPath(commonAncestor).contains(function (element) {
            return element.data('oe-model') === 'ir.ui.view'
        });
        if (!viewRoot) { return null; }
        // if viewRoot is the first link, don't edit it.
        return new CKEDITOR.dom.elementPath(commonAncestor, viewRoot)
                .contains('a', true);
    }


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
