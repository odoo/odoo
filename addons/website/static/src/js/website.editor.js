(function () {
    'use strict';

    var website = openerp.website;
    var _t = openerp._t;
    website.no_editor = !!$(document.documentElement).data('editable-no-editor');

    website.add_template_file('/website/static/src/xml/website.editor.xml');
    website.dom_ready.done(function () {
        var is_smartphone = $(document.body)[0].clientWidth < 767;

        if (!is_smartphone) {
            website.ready().then(website.init_editor);
        } else {
            var resize_smartphone = function () {
                is_smartphone = $(document.body)[0].clientWidth < 767;
                if (!is_smartphone) {
                    $(window).off("resize", resize_smartphone);
                    website.init_editor();
                }
            };
            $(window).on("resize", resize_smartphone);
        }

        $(document).on('click', 'a.js_link2post', function (ev) {
            ev.preventDefault();
            website.form(this.pathname, 'POST');
        });

        $(document).on('click', '.cke_editable label', function (ev) {
            ev.preventDefault();
        });

        $(document).on('submit', '.cke_editable form', function (ev) {
            // Disable form submition in editable mode
            ev.preventDefault();
        });

        $(document).on('hide.bs.dropdown', '.dropdown', function (ev) {
            // Prevent dropdown closing when a contenteditable children is focused
            if (ev.originalEvent
                    && $(ev.target).has(ev.originalEvent.target).length
                    && $(ev.originalEvent.target).is('[contenteditable]')) {
                ev.preventDefault();
            }
        });
    });

    /**
     * An editing host is an HTML element with @contenteditable=true, or the
     * child of a document in designMode=on (but that one's not supported)
     *
     * https://dvcs.w3.org/hg/editing/raw-file/tip/editing.html#editing-host
     */
    function is_editing_host(element) {
        return element.getAttribute('contentEditable') === 'true';
    }
    /**
     * Checks that both the element's content *and the element itself* are
     * editable: an editing host is considered non-editable because its content
     * is editable but its attributes should not be considered editable
     */
    function is_editable_node(element) {
        return !(element.data('oe-model') === 'ir.ui.view'
              || element.data('cke-realelement')
              || (is_editing_host(element) && element.getAttribute('attributeEditable') !== 'true')
              || element.isReadOnly());
    }

    function link_dialog(editor) {
        return new website.editor.RTELinkDialog(editor).appendTo(document.body);
    }
    function image_dialog(editor, image) {
        return new website.editor.MediaDialog(editor, image).appendTo(document.body);
    }

    // only enable editors manually
    CKEDITOR.disableAutoInline = true;
    // EDIT ALL THE THINGS
    CKEDITOR.dtd.$editable = _.omit(
        $.extend({}, CKEDITOR.dtd.$block, CKEDITOR.dtd.$inline),
        // well maybe not *all* the things
        'ul', 'ol', 'li', 'table', 'tr', 'th', 'td');
    // Disable removal of empty elements on CKEDITOR activation. Empty
    // elements are used for e.g. support of FontAwesome icons
    CKEDITOR.dtd.$removeEmpty = {};


    website.init_editor = function () {
        CKEDITOR.plugins.add('customdialogs', {
            // requires: 'link,image',
            init: function (editor) {
                editor.on('doubleclick', function (evt) {
                    var element = evt.data.element;
                    if ((element.is('img') || element.$.className.indexOf(' fa-') != -1) && is_editable_node(element)) {
                        image_dialog(editor, element);
                        return;
                    }
                    var parent = new CKEDITOR.dom.element(element.$.parentNode);
                    if (parent.$.className.indexOf('media_iframe_video') != -1 && is_editable_node(parent)) {
                        image_dialog(editor, parent);
                        return;
                    }

                    element = get_selected_link(editor) || evt.data.element;
                    if (!(element.is('a') && is_editable_node(element))) {
                        return;
                    }

                    editor.getSelection().selectElement(element);
                    link_dialog(editor);
                }, null, null, 500);

                //noinspection JSValidateTypes
                editor.addCommand('link', {
                    exec: function (editor) {
                        link_dialog(editor);
                        return true;
                    },
                    canUndo: false,
                    editorFocus: true,
                    context: 'a',
                });
                //noinspection JSValidateTypes
                editor.addCommand('cimage', {
                    exec: function (editor) {
                        image_dialog(editor);
                        return true;
                    },
                    canUndo: false,
                    editorFocus: true,
                    context: 'img',
                });

                editor.ui.addButton('Link', {
                    label: 'Link',
                    command: 'link',
                    toolbar: 'links,10',
                });
                editor.ui.addButton('Image', {
                    label: 'Image',
                    command: 'cimage',
                    toolbar: 'insert,10',
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

        CKEDITOR.plugins.add('customColor', {
            requires: 'panelbutton,floatpanel',
            init: function (editor) {
                function create_button (buttonID, label) {
                    var btnID = buttonID;
                    editor.ui.add(buttonID, CKEDITOR.UI_PANELBUTTON, {
                        label: label,
                        title: label,
                        modes: { wysiwyg: true },
                        editorFocus: true,
                        context: 'font',
                        panel: {
                            css: [  '/web/css/web.assets_common/' + (new Date().getTime()),
                                    '/web/css/website.assets_frontend/' + (new Date().getTime()),
                                    '/web/css/website.assets_editor/' + (new Date().getTime())],
                            attributes: { 'role': 'listbox', 'aria-label': label },
                        },
                        enable: function () {
                            this.setState(CKEDITOR.TRISTATE_OFF);
                        },
                        disable: function () {
                            this.setState(CKEDITOR.TRISTATE_DISABLED);
                        },
                        onBlock: function (panel, block) {
                            var self = this;
                            var html = openerp.qweb.render('website.colorpicker');
                            block.autoSize = true;
                            block.element.setHtml( html );
                            $(block.element.$).on('click', 'button', function () {
                                self.clicked(this);
                            });
                            if (btnID === "TextColor") {
                                $(".only-text", block.element.$).css("display", "block");
                                $(".only-bg", block.element.$).css("display", "none");
                            }
                            var $body = $(block.element.$).parents("body");
                            setTimeout(function () {
                                $body.css('background-color', '#fff');
                            }, 0);
                        },
                        getClasses: function () {
                            var self = this;
                            var classes = [];
                            var id = this._.id;
                            var block = this._.panel._.panel._.blocks[id];
                            var $root = $(block.element.$);
                            $root.find("button").map(function () {
                                var color = self.getClass(this);
                                if(color) classes.push( color );
                            });
                            return classes;
                        },
                        getClass: function (button) {
                            var color = btnID === "BGColor" ? $(button).attr("class") : $(button).attr("class").replace(/^bg-/i, 'text-');
                            return color.length && color;
                        },
                        clicked: function (button) {
                            var className = this.getClass(button);
                            var ancestor = editor.getSelection().getCommonAncestor();

                            editor.focus();
                            this._.panel.hide();
                            editor.fire('saveSnapshot');

                            // remove style
                            var classes = [];
                            var $ancestor = $(ancestor.$);
                            var $fonts = $(ancestor.$).find('font');
                            if (!ancestor.$.tagName) {
                                $ancestor = $ancestor.parent();
                            }
                            if ($ancestor.is('font')) {
                                $fonts = $fonts.add($ancestor[0]);
                            }

                            $fonts.filter("."+this.getClasses().join(",.")).map(function () {
                                var className = $(this).attr("class");
                                if (classes.indexOf(className) === -1) {
                                    classes.push(className);
                                }
                            });
                            for (var k in classes) {
                                editor.removeStyle( new CKEDITOR.style({
                                    element: 'font',
                                    attributes: { 'class': classes[k] },
                                }) );
                            }

                            // add new style
                            if (className) {
                                editor.applyStyle( new CKEDITOR.style({
                                    element: 'font',
                                    attributes: { 'class': className },
                                }) );
                            }
                            editor.fire('saveSnapshot');
                        }

                    });
                }
                create_button("BGColor", "Background Color");
                create_button("TextColor", "Text Color");
            }
        });

        CKEDITOR.plugins.add('oeref', {
            requires: 'widget',

            init: function (editor) {
                var specials = {
                    // Can't find the correct ACL rule to only allow img tags
                    image: { content: '*' },
                    html: { text: '*' },
                    monetary: {
                        text: {
                            selector: 'span.oe_currency_value',
                            allowedContent: { }
                        }
                    }
                };
                _(specials).each(function (editable, type) {
                    editor.widgets.add(type, {
                        draggable: false,
                        editables: editable,
                        upcast: function (el) {
                            return  el.attributes['data-oe-type'] === type;

                        }
                    });
                });
                editor.widgets.add('oeref', {
                    draggable: false,
                    editables: {
                        text: {
                            selector: '*',
                            allowedContent: { }
                        },
                    },
                    upcast: function (el) {
                        var type = el.attributes['data-oe-type'];
                        if (!type || (type in specials)) {
                            return false;
                        }
                        if (el.attributes['data-oe-original']) {
                            while (el.children.length) {
                                el.children[0].remove();
                            }
                            el.add(new CKEDITOR.htmlParser.text(
                                el.attributes['data-oe-original']
                            ));
                        }
                        return true;
                    }
                });

                editor.widgets.add('icons', {
                    draggable: false,

                    init: function () {
                        this.on('edit', function () {
                            new website.editor.MediaDialog(editor, this.element)
                                .appendTo(document.body);
                        });
                    },
                    upcast: function (el) {
                        return el.hasClass('fa')
                            // ignore ir.ui.view (other data-oe-model should
                            // already have been matched by oeref and
                            // monetary?
                            && !el.attributes['data-oe-model'];
                    }
                });
            }
        });

        var editor = new website.EditorBar();
        var $body = $(document.body);
        editor.prependTo($body).then(function () {
            if (location.search.indexOf("enable_editor") >= 0) {
                editor.edit();
            }
        });
        website.editor_bar = editor;
    };

    /* ----- TOP EDITOR BAR FOR ADMIN ---- */
    website.EditorBar = openerp.Widget.extend({
        template: 'website.editorbar',
        events: {
            'click button[data-action=save]': 'save',
            'click a[data-action=cancel]': 'cancel',
        },
        start: function() {
            var self = this;
            this.saving_mutex = new openerp.Mutex();

            this.$buttons = {
                edit: this.$el.parents().find('button[data-action=edit]'),
                save: this.$('button[data-action=save]'),
                cancel: this.$('button[data-action=cancel]'),
            };

            this.$('#website-top-edit').hide();
            this.$('#website-top-view').show();

            var $edit_button = this.$buttons.edit
                    .prop('disabled', website.no_editor);
            if (website.no_editor) {
                var help_text = $(document.documentElement).data('editable-no-editor');
                $edit_button.parent()
                    // help must be set on form above button because it does
                    // not appear on disabled button
                    .attr('title', help_text);
            }

            $('.dropdown-toggle').dropdown();

            this.$buttons.edit.click(function(ev) {
                self.edit();
            });

            this.rte = new website.RTE(this);
            this.rte.on('change', this, this.proxy('rte_changed'));
            this.rte.on('rte:ready', this, function () {
                self.setup_hover_buttons();
                self.trigger('rte:ready');
            });

            this.rte.appendTo(this.$('#website-top-edit .nav.js_editor_placeholder'));
            return this._super.apply(this, arguments);
            
        },
        edit: function () {
            this.$buttons.edit.prop('disabled', true);
            this.$('#website-top-view').hide();
            this.$el.show();
            this.$('#website-top-edit').show();
            $('.css_non_editable_mode_hidden').removeClass("css_non_editable_mode_hidden");

            this.rte.start_edition();
            this.trigger('rte:called');
        },
        rte_changed: function () {
            this.$buttons.save.prop('disabled', false);
        },
        save: function () {
            var self = this;

            observer.disconnect();
            var editor = this.rte.editor;
            var root = editor.element && editor.element.$;
            try {
                editor.destroy();
            }
            catch(err) {
                // Hack to avoid the lost of all changes because ckeditor fails in destroy
                console.log("Error in editor.destroy() : " + err.toString() + "\n  " + err.stack);
            }
            // FIXME: select editables then filter by dirty?
            var defs = this.rte.fetch_editables(root)
                .filter('.oe_dirty')
                .removeAttr('contentEditable')
                .removeClass('oe_dirty oe_editable cke_focus oe_carlos_danger')
                .map(function () {
                    var $el = $(this);
                    // TODO: Add a queue with concurrency limit in webclient
                    // https://github.com/medikoo/deferred/blob/master/lib/ext/function/gate.js
                    return self.saving_mutex.exec(function () {
                        return self.saveElement($el)
                            .then(undefined, function (thing, response) {
                                // because ckeditor regenerates all the dom,
                                // we can't just setup the popover here as
                                // everything will be destroyed by the DOM
                                // regeneration. Add markings instead, and
                                // returns a new rejection with all relevant
                                // info
                                var id = _.uniqueId('carlos_danger_');
                                $el.addClass('oe_dirty oe_carlos_danger');
                                $el.addClass(id);
                                return $.Deferred().reject({
                                    id: id,
                                    error: response.data,
                                });
                            });
                    });
                }).get();
            return $.when.apply(null, defs).then(function () {
                website.reload();
            }, function (failed) {
                // If there were errors, re-enable edition
                self.rte.start_edition(true).then(function () {
                    // jquery's deferred being a pain in the ass
                    if (!_.isArray(failed)) { failed = [failed]; }

                    _(failed).each(function (failure) {
                        var html = failure.error.exception_type === "except_osv";
                        if (html) {
                            var msg = $("<div/>").text(failure.error.message).html();
                            var data = msg.substring(3,msg.length-2).split(/', u'/);
                            failure.error.message = '<b>' + data[0] + '</b><br/>' + data[1];
                        }
                        $(root).find('.' + failure.id)
                            .removeClass(failure.id)
                            .popover({
                                html: html,
                                trigger: 'hover',
                                content: failure.error.message,
                                placement: 'auto top',
                            })
                            // Force-show popovers so users will notice them.
                            .popover('show');
                    });
                });
            });
        },
        /**
         * Saves an RTE content, which always corresponds to a view section (?).
         */
        saveElement: function ($el) {
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
            new $.Deferred(function (d) {
                var $dialog = $(openerp.qweb.render('website.editor.discard')).appendTo(document.body);
                $dialog.on('click', '.btn-danger', function () {
                    d.resolve();
                }).on('hidden.bs.modal', function () {
                    d.reject();
                });
                d.always(function () {
                    $dialog.remove();
                });
                $dialog.modal('show');
            }).then(function () {
                website.reload();
            })
        },

        /**
         * Creates a "hover" button for link edition
         *
         * @param {Function} editfn edition function, called when clicking the button
         * @returns {jQuery}
         */
        make_hover_button_link: function (editfn) {
            return $(openerp.qweb.render('website.editor.hoverbutton.link', {}))
                .hide()
                .click(function (e) {
                    e.preventDefault();
                    e.stopPropagation();
                    editfn.call(this, e);
                })
                .appendTo(document.body);
        },

        /**
         * Creates a "hover" button for image
         *
         * @param {Function} editfn edition function, called when clicking the button
         * @param {Function} stylefn edition style function, called when clicking the button
         * @returns {jQuery}
         */
        make_hover_button_image: function (editfn, stylefn) {
            var $div = $(openerp.qweb.render('website.editor.hoverbutton.media', {}))
                .hide()
                .appendTo(document.body);

            $div.find('[data-toggle="dropdown"]').dropdown();
            $div.find(".hover-edition-button").click(function (e) {
                e.preventDefault();
                e.stopPropagation();
                editfn.call(this, e);
            });
            if (stylefn) {
                $div.find(".hover-style-button").click(function (e) {
                    e.preventDefault();
                    e.stopPropagation();
                    stylefn.call(this, e);
                });
            }
            return $div;
        },
        /**
         * For UI clarity, during RTE edition when the user hovers links and
         * images a small button should appear to make the capability clear,
         * as not all users think of double-clicking the image or link.
         */
        setup_hover_buttons: function () {
            var editor = this.rte.editor;
            var $link_button = this.make_hover_button_link(function () {
                var sel = new CKEDITOR.dom.element(previous);
                editor.getSelection().selectElement(sel);
                if(sel.hasClass('fa')) {
                    new website.editor.MediaDialog(editor, previous)
                        .appendTo(document.body);
                } else if (previous.tagName.toUpperCase() === 'A') {
                    link_dialog(editor);
                }
                $link_button.hide();
                previous = null;
            });

            function is_icons_widget(element) {
                var w = editor.widgets.getByElement(element);
                return w && w.name === 'icons';
            }

            // previous is the state of the button-trigger: it's the
            // currently-ish hovered element which can trigger a button showing.
            // -ish, because when moving to the button itself ``previous`` is
            // still set to the element having triggered showing the button.
            var previous;
            $(editor.element.$).on('mouseover', 'a', function () {
                // Back from edit button -> ignore
                if (previous && previous === this) { return; }

                // hover button should appear for "editable" links and images
                // (img and a nodes whose *attributes* are editable, they
                // can not be "editing hosts") *or* for non-editing-host
                // elements bearing an ``fa`` class. These should have been
                // made into CKE widgets which are editing hosts by
                // definition, so instead check if the element has been
                // converted/upcasted to an fa widget
                var selected = new CKEDITOR.dom.element(this);
                if (!(is_editable_node(selected) || is_icons_widget(selected))) {
                    return;
                }

                previous = this;
                var $selected = $(this);
                var position = $selected.offset();
                $link_button.show().offset({
                    top: $selected.outerHeight()
                            + position.top,
                    left: $selected.outerWidth() / 2
                            + position.left
                            - $link_button.outerWidth() / 2
                })
            }).on('mouseleave', 'a, img, .fa', function (e) {
                var current = document.elementFromPoint(e.clientX, e.clientY);
                if (current === $link_button[0] || $(current).parent()[0] === $link_button[0]) {
                    return;
                }
                $link_button.hide();
                previous = null;
            });
        }
    });
    
    website.EditorBarCustomize = openerp.Widget.extend({
        events: {
            'mousedown a.dropdown-toggle': 'load_menu',
            'click ul a[data-view-id]': 'do_customize',
        },
        start: function() {
            var self = this;
            this.$menu = self.$el.find('ul');
            this.view_name = $(document.documentElement).data('view-xmlid');
            if (!this.view_name) {
                this.$el.hide();
            }
            this.loaded = false;
        },
        load_menu: function () {
            var self = this;
            if(this.loaded) {
                return;
            }
            openerp.jsonRpc('/website/customize_template_get', 'call', { 'xml_id': this.view_name }).then(
                function(result) {
                    _.each(result, function (item) {
                        if (item.xml_id === "website.debugger" && !window.location.search.match(/[&?]debug(&|$)/)) return;
                        if (item.header) {
                            self.$menu.append('<li class="dropdown-header">' + item.name + '</li>');
                        } else {
                            self.$menu.append(_.str.sprintf('<li role="presentation"><a href="#" data-view-id="%s" role="menuitem"><strong class="fa fa%s-square-o"></strong> %s</a></li>',
                                item.id, item.active ? '-check' : '', item.name));
                        }
                    });
                    self.loaded = true;
                }
            );
        },
        do_customize: function (event) {
            var view_id = $(event.currentTarget).data('view-id');
            return openerp.jsonRpc('/web/dataset/call_kw', 'call', {
                model: 'ir.ui.view',
                method: 'toggle',
                args: [],
                kwargs: {
                    ids: [parseInt(view_id, 10)],
                    context: website.get_context()
                }
            }).then( function() {
                window.location.reload();
            });
        },
    });

    $(document).ready(function() {
        var editorBarCustomize = new website.EditorBarCustomize();
        editorBarCustomize.setElement($('li[id=customize-menu]'));
        editorBarCustomize.start();
    });

    var blocks_selector = _.keys(CKEDITOR.dtd.$block).join(',');
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

        /**
         * In Webkit-based browsers, triple-click will select a paragraph up to
         * the start of the next "paragraph" including any empty space
         * inbetween. When said paragraph is removed or altered, it nukes
         * the empty space and brings part of the content of the next
         * "paragraph" (which may well be e.g. an image) into the current one,
         * completely fucking up layouts and breaking snippets.
         *
         * Try to fuck around with selections on triple-click to attempt to
         * fix this garbage behavior.
         *
         * Note: for consistent behavior we may actually want to take over
         * triple-clicks, in all browsers in order to ensure consistent cross-
         * platform behavior instead of being at the mercy of rendering engines
         * & platform selection quirks?
         */
        webkitSelectionFixer: function (root) {
            root.addEventListener('click', function (e) {
                // only webkit seems to have a fucked up behavior, ignore others
                // FIXME: $.browser goes away in jquery 1.9...
                if (!$.browser.webkit) { return; }
                // http://www.w3.org/TR/DOM-Level-2-Events/events.html#Events-eventgroupings-mouseevents
                // The detail attribute indicates the number of times a mouse button has been pressed
                // we just want the triple click
                if (e.detail !== 3) { return; }
                e.preventDefault();

                // Get closest block-level element to the triple-clicked
                // element (using ckeditor's block list because why not)
                var $closest_block = $(e.target).closest(blocks_selector);

                // manually set selection range to the content of the
                // triple-clicked block-level element, to avoid crossing over
                // between block-level elements
                document.getSelection().selectAllChildren($closest_block[0]);
            });
        },
        tableNavigation: function (root) {
            var self = this;
            $(root).on('keydown', function (e) {
                // ignore non-TAB
                if (e.which !== 9) { return; }

                if (self.handleTab(e)) {
                    e.preventDefault();
                }
            });
        },
        /**
         * Performs whatever operation is necessary on a [TAB] hit, returns
         * ``true`` if the event's default should be cancelled (if the TAB was
         * handled by the function)
         */
        handleTab: function (event) {
            var forward = !event.shiftKey;

            var root = window.getSelection().getRangeAt(0).commonAncestorContainer;
            var $cell = $(root).closest('td,th');

            if (!$cell.length) { return false; }

            var cell = $cell[0];

            // find cell in same row
            var row = cell.parentNode;
            var sibling = row.cells[cell.cellIndex + (forward ? 1 : -1)];
            if (sibling) {
                document.getSelection().selectAllChildren(sibling);
                return true;
            }

            // find cell in previous/next row
            var table = row.parentNode;
            var sibling_row = table.rows[row.rowIndex + (forward ? 1 : -1)];
            if (sibling_row) {
                var new_cell = sibling_row.cells[forward ? 0 : sibling_row.cells.length - 1];
                document.getSelection().selectAllChildren(new_cell);
                return true;
            }

            // at edge cells, copy word/openoffice behavior: if going backwards
            // from first cell do nothing, if going forwards from last cell add
            // a row
            if (forward) {
                var row_size = row.cells.length;
                var new_row = document.createElement('tr');
                while(row_size--) {
                    var newcell = document.createElement('td');
                    // zero-width space
                    newcell.textContent = '\u200B';
                    new_row.appendChild(newcell);
                }
                table.appendChild(new_row);
                document.getSelection().selectAllChildren(new_row.cells[0]);
            }

            return true;
        },
        /**
         * Makes the page editable
         *
         * @param {Boolean} [restart=false] in case the edition was already set
         *                                  up once and is being re-enabled.
         * @returns {$.Deferred} deferred indicating when the RTE is ready
         */
        start_edition: function (restart) {
            var self = this;
            // create a single editor for the whole page
            var root = document.getElementById('wrapwrap');
            if (!restart) {
                $(root).on('dragstart', 'img', function (e) {
                    e.preventDefault();
                });
                this.webkitSelectionFixer(root);
                this.tableNavigation(root);
            }
            var def = $.Deferred();
            var editor = this.editor = CKEDITOR.inline(root, self._config());
            editor.on('instanceReady', function () {
                $("[data-oe-type=selection]").attr("contenteditable",false);
                editor.setReadOnly(false);
                // ckeditor set root to editable, disable it (only inner
                // sections are editable)
                // FIXME: are there cases where the whole editor is editable?
                editor.editable().setReadOnly(true);

                self.setup_editables(root);

                try {
                    // disable firefox's broken table resizing thing
                    document.execCommand("enableObjectResizing", false, "false");
                    document.execCommand("enableInlineTableEditing", false, "false");
                } catch (e) {}

                // detect & setup any CKEDITOR widget within a newly dropped
                // snippet. There does not seem to be a simple way to do it for
                // HTML not inserted via ckeditor APIs:
                // https://dev.ckeditor.com/ticket/11472
                $(document.body)
                    .off('snippet-dropped')
                    .on('snippet-dropped', function (e, el) {
                        // CKEDITOR data processor extended by widgets plugin
                        // to add wrappers around upcasting elements
                        el.innerHTML = editor.dataProcessor.toHtml(el.innerHTML, {
                            fixForBody: false,
                            dontFilter: true,
                        });
                        // then repository.initOnAll() handles the conversion
                        // from wrapper to actual widget instance (or something
                        // like that).
                        setTimeout(function () {
                            editor.widgets.initOnAll();
                        }, 0);
                    });

                self.trigger('rte:ready');
                def.resolve();
            });
            return def;
        },

        setup_editables: function (root) {
            // selection of editable sub-items was previously in
            // EditorBar#edit, but for some unknown reason the elements were
            // apparently removed and recreated (?) at editor initalization,
            // and observer setup was lost.
            var self = this;
            // setup dirty-marking for each editable element
            this.fetch_editables(root)
                .addClass('oe_editable')
                .each(function () {
                    var node = this;
                    var $node = $(node);
                    // only explicitly set contenteditable on view sections,
                    // cke widgets system will do the widgets themselves
                    if ($node.data('oe-model') === 'ir.ui.view') {
                        node.contentEditable = true;
                    }

                    observer.observe(node, OBSERVER_CONFIG);
                    $node.one('content_changed', function () {
                        $node.addClass('oe_dirty');
                        self.trigger('change');
                    });
                });
        },

        fetch_editables: function (root) {
            return $(root).find('[data-oe-model]')
                .not('[data-oe-type = "selection"]')
                .not('link, script')
                .not('.oe_snippet_editor');
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
                'a11yhelp', 'basicstyles', 'blockquote',
                'clipboard', 'colorbutton', 'colordialog', 'dialogadvtab',
                'elementspath', /*'enterkey',*/ 'entities', 'filebrowser',
                'find', 'floatingspace','format', 'htmlwriter', 'iframe',
                'indentblock', 'indentlist', 'justify',
                'list', 'pastefromword', 'pastetext', 'preview',
                'removeformat', 'resize', 'save', 'selectall', 'stylescombo',
                'table', 'templates', 'toolbar', 'undo', 'wysiwygarea'
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
                extraPlugins: 'customColor,sharedspace,customdialogs,tablebutton,oeref',
                // Place toolbar in controlled location
                sharedSpaces: { top: 'oe_rte_toolbar' },
                toolbar: [{
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
                ],
            };
        },
    });

    website.editor = { };
    website.editor.Dialog = openerp.Widget.extend({
        events: {
            'hidden.bs.modal': 'destroy',
            'click button.save': 'save',
            'click button[data-dismiss="modal"]': 'cancel',
        },
        init: function (editor) {
            this._super();
            this.editor = editor;
        },
        start: function () {
            var sup = this._super();
            this.$el.modal({backdrop: 'static'});
            this.$('input:first').focus();
            return sup;
        },
        save: function () {
            this.close();
            this.trigger("saved");
        },
        cancel: function () {
            this.trigger("cancel");
        },
        close: function () {
            this.$el.modal('hide');
        },
    });

    website.editor.LinkDialog = website.editor.Dialog.extend({
        template: 'website.editor.dialog.link',
        events: _.extend({}, website.editor.Dialog.prototype.events, {
            'change :input.url-source': 'changed',
            'keyup :input.url': 'onkeyup',
            'keyup :input': 'preview',
            'mousedown': function (e) {
                var $target = $(e.target).closest('.list-group-item:has(.url-source)');
                if (!$target.length || $target.hasClass('active')) {
                    // clicked outside groups, or clicked in active groups
                    return;
                }
                $target.find("input.url-source").change();
            },
            'click button.remove': 'remove_link',
            'change input#link-text': function (e) {
                this.text = $(e.target).val();
            },
            'change .link-style': function (e) {
                this.preview();
            },
        }),
        init: function (editor) {
            this._super(editor);
            this.text = null;
            // Store last-performed request to be able to cancel/abort it.
            this.page_exists_req = null;
            this.search_pages_req = null;
        },
        start: function () {
            var self = this;
            var last;
            this.$('#link-page').select2({
                minimumInputLength: 1,
                placeholder: _t("New or existing page"),
                query: function (q) {
                    if (q.term == last) return;
                    last = q.term;
                    $.when(
                        self.page_exists(q.term),
                        self.fetch_pages(q.term)
                    ).then(function (exists, results) {
                        var rs = _.map(results, function (r) {
                            return { id: r.loc, text: r.loc, };
                        });
                        if (!exists) {
                            rs.push({
                                create: true,
                                id: q.term,
                                text: _.str.sprintf(_t("Create page '%s'"), q.term),
                            });
                        }
                        q.callback({
                            more: false,
                            results: rs
                        });
                    }, function () {
                        q.callback({more: false, results: []});
                    });
                },
            });
            return this._super().then(this.proxy('bind_data'));
        },
        get_data: function (test) {
            var self = this,
                def = new $.Deferred(),
                $e = this.$('.active input.url-source').filter(':input'),
                val = $e.val(),
                label = this.$('#link-text').val() || val;

            if (test !== false && (!val || !$e[0].checkValidity())) {
                // FIXME: error message
                $e.closest('.form-group').addClass('has-error');
                $e.focus();
                def.reject();
            }

            var style = this.$("input[name='link-style-type']:checked").val();
            var size = this.$("input[name='link-style-size']:checked").val();
            var classes = (style && style.length ? "btn " : "") + style + " " + size;

            if ($e.hasClass('email-address') && $e.val().indexOf("@") !== -1) {
                def.resolve('mailto:' + val, false, label, classes);
            } else if ($e.val() && $e.val().length && $e.hasClass('page')) {
                var data = $e.select2('data');
                if (!data.create) {
                    def.resolve(data.id, false, label || data.text, classes);
                } else {
                    // Create the page, get the URL back
                    $.get(_.str.sprintf(
                            '/website/add/%s?noredirect=1', encodeURI(data.id)))
                        .then(function (response) {
                            def.resolve(response, false, data.id, classes);
                        });
                }
            } else {
                def.resolve(val, this.$('input.window-new').prop('checked'), label, classes);
            }
            return def;
        },
        save: function () {
            var self = this;
            var _super = this._super.bind(this);
            return this.get_data()
                .then(function (url, new_window, label, classes) {
                    self.make_link(url, new_window, label, classes);
                }).then(_super);
        },
        make_link: function (url, new_window, label, classes) {
        },
        bind_data: function () {
            var self = this;
            var href = this.element && (this.element.data( 'cke-saved-href')
                                    ||  this.element.getAttribute('href'));
            var new_window = this.element
                        ? this.element.getAttribute('target') === '_blank'
                        : false;
            var text = this.element ? this.element.getText() : '';
            if (!text.length) {
                if (this.editor) {
                    text = this.editor.getSelection().getSelectedText();
                } else {
                    text = this.data.name;
                    href = this.data.url;
                    new_window = this.data.new_window;
                }
            }

            this.$('input#link-text').val(text);
            this.$('input.window-new').prop('checked', new_window);

            var classes = this.element && this.element.$.className;
            if (classes) {
                this.$('input[value!=""]').each(function () {
                    var $option = $(this);
                    if (classes.indexOf($option.val()) !== -1) {
                        $option.attr("checked", "checked");
                    }
                });
            }

            var match, $control;
            if (href && (match = /mailto:(.+)/.exec(href))) {
                this.$('input.email-address').val(match[1]).change();
            }
            if (href && !$control) {
                this.page_exists(href).then(function (exist) {
                    if (exist) {
                        self.$('#link-page').select2('data', {'id': href, 'text': href});
                    } else {
                        self.$('input.url').val(href).change();
                        self.$('input.window-new').closest("div").show();
                    }
                });
            }
            this.preview();
        },
        changed: function (e) {
            var $e = $(e.target);
            this.$('.url-source').filter(':input').not($e).val('')
                    .filter(function () { return !!$(this).data('select2'); })
                    .select2('data', null);
            $e.closest('.list-group-item')
                .addClass('active')
                .siblings().removeClass('active')
                .addBack().removeClass('has-error');
            this.preview();
        },
        call: function (method, args, kwargs) {
            var self = this;
            var req = method + '_req';

            if (this[req]) { this[req].abort(); }

            return this[req] = openerp.jsonRpc('/web/dataset/call_kw', 'call', {
                model: 'website',
                method: method,
                args: args,
                kwargs: kwargs,
            }).always(function () {
                self[req] = null;
            });
        },
        page_exists: function (term) {
            return this.call('page_exists', [null, term], {
                context: website.get_context(),
            });
        },
        fetch_pages: function (term) {
            return this.call('search_pages', [null, term], {
                limit: 9,
                context: website.get_context(),
            });
        },
        onkeyup: function (e) {
            var $e = $(e.target);
            var is_link = ($e.val()||'').length && $e.val().indexOf("@") === -1;
            this.$('input.window-new').closest("div").toggle(is_link);
            this.preview();
        },
        preview: function () {
            var $preview = this.$("#link-preview");
            this.get_data(false).then(function (url, new_window, label, classes) {
                $preview.attr("target", new_window ? '_blank' : "")
                    .text((label && label.length ? label : url))
                    .attr("class", classes);
            });
        }
    });
    website.editor.RTELinkDialog = website.editor.LinkDialog.extend({
        start: function () {
            var element;
            if ((element = this.get_selected_link()) && element.hasAttribute('href')) {
                this.editor.getSelection().selectElement(element);
            }
            this.element = element;
            if (element) {
                this.add_removal_button();
            }

            return this._super();
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
        make_link: function (url, new_window, label, classes) {
            var attributes = {href: url, 'data-cke-saved-href': url};
            var to_remove = [];
            if (new_window) {
                attributes['target'] = '_blank';
            } else {
                to_remove.push('target');
            }
            if (classes && classes.length) {
                attributes['class'] = classes;
            }

            if (this.element) {
                this.element.setAttributes(attributes);
                this.element.removeAttributes(to_remove);
                if (this.text) { this.element.setText(this.text); }
            } else {
                var selection = this.editor.getSelection();
                var range = selection.getRanges(true)[0];

                if (range.collapsed) {
                    //noinspection JSPotentiallyInvalidConstructorUsage
                    var text = new CKEDITOR.dom.text(
                        this.text || label || url);
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
        /**
         * CKEDITOR.plugins.link.getSelectedLink ignores the editor's root,
         * if the editor is set directly on a link it will thus not work.
         */
        get_selected_link: function () {
            return get_selected_link(this.editor);
        },
    });

    website.editor.Media = openerp.Widget.extend({
        init: function (parent, editor, media) {
            this._super();
            this.parent = parent;
            this.editor = editor;
            this.media = media;
        },
        start: function () {
            this.$preview = this.$('.preview-container').detach();
            return this._super();
        },
        search: function (needle) {
        },
        save: function () {
        },
        clear: function () {
        },
        cancel: function () {
        },
        close: function () {
        },
    });
    website.editor.MediaDialog = website.editor.Dialog.extend({
        template: 'website.editor.dialog.media',
        events : _.extend({}, website.editor.Dialog.prototype.events, {
            'input input#icon-search': 'search',
        }),

        init: function (editor, media) {
            this._super(editor);
            this.editor = editor;
            this.page = 0;
            this.media = media;
        },
        start: function () {
            var self = this;

            if (this.editor.getSelection) {
                var selection = this.editor.getSelection();
                this.range = selection.getRanges(true)[0];
            }

            this.imageDialog = new website.editor.RTEImageDialog(this, this.editor, this.media);
            this.imageDialog.appendTo(this.$("#editor-media-image"));
            this.iconDialog = new website.editor.FontIconsDialog(this, this.editor, this.media);
            this.iconDialog.appendTo(this.$("#editor-media-icon"));
            this.videoDialog = new website.editor.VideoDialog(this, this.editor, this.media);
            this.videoDialog.appendTo(this.$("#editor-media-video"));

            this.active = this.imageDialog;

            $('a[data-toggle="tab"]').on('shown.bs.tab', function (event) {
                if ($(event.target).is('[href="#editor-media-image"]')) {
                    self.active = self.imageDialog;
                    self.$('li.search, li.previous, li.next').removeClass("hidden");
                } else if ($(event.target).is('[href="#editor-media-icon"]')) {
                    self.active = self.iconDialog;
                    self.$('li.search, li.previous, li.next').removeClass("hidden");
                    self.$('.nav-tabs li.previous, .nav-tabs li.next').addClass("hidden");
                } else if ($(event.target).is('[href="#editor-media-video"]')) {
                    self.active = self.videoDialog;
                    self.$('.nav-tabs li.search').addClass("hidden");
                }
            });

            if (this.media) {
                if (this.media.$.nodeName === "IMG") {
                    this.$('[href="#editor-media-image"]').tab('show');
                } else if (this.media.$.className.match(/(^|\s)media_iframe_video($|\s)/)) {
                    this.$('[href="#editor-media-video"]').tab('show');
                } else if (this.media.$.className.match(/(^|\s)fa($|\s)/)) {
                    this.$('[href="#editor-media-icon"]').tab('show');
                }

                if ($(this.media.$).parent().data("oe-field") === "image") {
                    this.$('[href="#editor-media-video"], [href="#editor-media-icon"]').addClass('hidden');
                }
            }

            return this._super();
        },
        save: function () {
            var self = this;
            if (self.media) {
                this.media.$.innerHTML = "";
                if (this.active !== this.imageDialog) {
                    this.imageDialog.clear();
                }
                if (this.active !== this.iconDialog) {
                    this.iconDialog.clear();
                }
                if (this.active !== this.videoDialog) {
                    this.videoDialog.clear();
                }
            } else {
                this.media = new CKEDITOR.dom.element("img");
                self.range.insertNode(this.media);
                self.range.selectNodeContents(this.media);
                this.active.media = this.media;
            }

            var $el = $(self.active.media.$);

            this.active.save();

            this.media.$.className = this.media.$.className.replace(/\s+/g, ' ');

            setTimeout(function () {
                if(self.range) self.range.select();
                $el.trigger("saved", self.active.media.$);
                $(document.body).trigger("media-saved", [$el[0], self.active.media.$]);
            },0);

            this._super();
        },
        searchTimer: null,
        search: function () {
            var self = this;
            var needle = this.$("input#icon-search").val();
            clearTimeout(this.searchTimer);
            this.searchTimer = setTimeout(function () {
                self.active.search(needle || "");
            },250);
        }
    });

    /**
     * ImageDialog widget. Lets users change an image, including uploading a
     * new image in OpenERP or selecting the image style (if supported by
     * the caller).
     *
     * Initialized as usual, but the caller can hook into two events:
     *
     * @event start({url, style}) called during dialog initialization and
     *                            opening, the handler can *set* the ``url``
     *                            and ``style`` properties on its parameter
     *                            to provide these as default values to the
     *                            dialog
     * @event save({url, style}) called during dialog finalization, the handler
     *                           is provided with the image url and style
     *                           selected by the users (or possibly the ones
     *                           originally passed in)
     */
    var IMAGES_PER_ROW = 6;
    var IMAGES_ROWS = 2;
    website.editor.ImageDialog = website.editor.Media.extend({
        template: 'website.editor.dialog.image',
        events: _.extend({}, website.editor.Dialog.prototype.events, {
            'change .url-source': function (e) {
                this.changed($(e.target));
            },
            'click button.filepicker': function () {
                var filepicker = this.$('input[type=file]');
                if (!_.isEmpty(filepicker)){
                    filepicker[0].click();
                }
            },
            'click .js_disable_optimization': function () {
                this.$('input[name="disable_optimization"]').val('1');
                var filepicker = this.$('button.filepicker');
                if (!_.isEmpty(filepicker)){
                    filepicker[0].click();
                }
            },
            'change input[type=file]': 'file_selection',
            'submit form': 'form_submit',
            'change input.url': "change_input",
            'keyup input.url': "change_input",
            //'change select.image-style': 'preview_image',
            'click .existing-attachments img': 'select_existing',
            'click .existing-attachment-remove': 'try_remove',
        }),

        init: function (parent, editor, media) {
            this.page = 0;
            this._super(parent, editor, media);
        },
        start: function () {
            var self = this;
            var res = this._super();

            var o = { url: null };
            // avoid typos, prevent addition of new properties to the object
            Object.preventExtensions(o);
            this.trigger('start', o);

            this.parent.$(".pager > li").click(function (e) {
                e.preventDefault();
                var $target = $(e.currentTarget);
                if ($target.hasClass('disabled')) {
                    return;
                }
                self.page += $target.hasClass('previous') ? -1 : 1;
                self.display_attachments();
            });

            this.set_image(o.url);

            return res;
        },
        save: function () {
            if (!this.link) {
                this.link = this.$(".existing-attachments img:first").attr('src');
            }
            this.trigger('save', {
                url: this.link
            });
            this.media.renameNode("img");
            $(this.media).attr('src', this.link);
            return this._super();
        },
        clear: function () {
            this.media.$.className = this.media.$.className.replace(/(^|\s)(img(\s|$)|img-[^\s]*)/g, ' ');
        },
        cancel: function () {
            this.trigger('cancel');
        },

        change_input: function (e) {
            var $input = $(e.target);
            var $button = $input.parent().find("button");
            if ($input.val() === "") {
                $button.addClass("btn-default").removeClass("btn-primary");
            } else {
                $button.removeClass("btn-default").addClass("btn-primary");
            }
        },

        search: function (needle) {
            var self = this;
            this.fetch_existing(needle).then(function () {
                self.selected_existing(self.$('input.url').val());
            });
        },

        set_image: function (url, error) {
            var self = this;
            if (url) this.link = url;
            this.$('input.url').val('');
            this.fetch_existing().then(function () {
                self.selected_existing(url);
            });
        },

        form_submit: function (event) {
            var self = this;
            var $form = this.$('form[action="/website/attach"]');
            if (!$form.find('input[name="upload"]').val().length) {
                var url = $form.find('input[name="url"]').val();
                if (this.selected_existing(url).size()) {
                    event.preventDefault();
                    return false;
                }
            }
            var callback = _.uniqueId('func_');
            this.$('input[name=func]').val(callback);
            window[callback] = function (attachments, error) {
                delete window[callback];
                self.file_selected(attachments[0]['website_url'], error);
            };
        },
        file_selection: function () {
            this.$el.addClass('nosave');
            this.$('form').removeClass('has-error').find('.help-block').empty();
            this.$('button.filepicker').removeClass('btn-danger btn-success');
            this.$('form').submit();
        },
        file_selected: function(url, error) {
            var $button = this.$('button.filepicker');
            if (!error) {
                $button.addClass('btn-success');
            } else {
                url = null;
                this.$('form').addClass('has-error')
                    .find('.help-block').text(error);
                $button.addClass('btn-danger');
            }
            this.set_image(url, error);
            // auto save and close popup
            this.parent.save();
        },

        fetch_existing: function (needle) {
            var domain = [['res_model', '=', 'ir.ui.view'], '|',
                        ['mimetype', '=', false], ['mimetype', '=like', 'image/%']];
            if (needle && needle.length) {
                domain.push('|', ['datas_fname', 'ilike', needle], ['name', 'ilike', needle]);
            }
            return openerp.jsonRpc('/web/dataset/call_kw', 'call', {
                model: 'ir.attachment',
                method: 'search_read',
                args: [],
                kwargs: {
                    fields: ['name', 'website_url'],
                    domain: domain,
                    order: 'id desc',
                    context: website.get_context(),
                }
            }).then(this.proxy('fetched_existing'));
        },
        fetched_existing: function (records) {
            this.records = records;
            this.display_attachments();
        },
        display_attachments: function () {
            this.$('.help-block').empty();
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
            this.parent.$('.pager')
                .find('li.previous').toggleClass('disabled', (from === 0)).end()
                .find('li.next').toggleClass('disabled', (from + per_screen >= records.length));
        },
        select_existing: function (e) {
            var link = $(e.currentTarget).attr('src');
            this.link = link;
            this.selected_existing(link);
        },
        selected_existing: function (link) {
            this.$('.existing-attachment-cell.media_selected').removeClass("media_selected");
            var $select = this.$('.existing-attachment-cell img').filter(function () {
                return $(this).attr("src") == link;
            }).first();
            $select.parent().addClass("media_selected");
            return $select;
        },

        try_remove: function (e) {
            var $help_block = this.$('.help-block').empty();
            var self = this;
            var $a = $(e.target);
            var id = parseInt($a.data('id'), 10);
            var attachment = _.findWhere(this.records, {id: id});
            var $both = $a.parent().children();

            $both.css({borderWidth: "5px", borderColor: "#f00"});

            return openerp.jsonRpc('/web/dataset/call_kw', 'call', {
                model: 'ir.attachment',
                method: 'try_remove',
                args: [],
                kwargs: {
                    ids: [id],
                    context: website.get_context()
                }
            }).then(function (prevented) {
                if (_.isEmpty(prevented)) {
                    self.records = _.without(self.records, attachment);
                    self.display_attachments();
                    return;
                }
                $both.css({borderWidth: "", borderColor: ""});
                $help_block.replaceWith(openerp.qweb.render(
                    'website.editor.dialog.image.existing.error', {
                        views: prevented[id]
                    }
                ));
            });
        },
    });

    website.editor.RTEImageDialog = website.editor.ImageDialog.extend({
        init: function (parent, editor, media) {
            this._super(parent, editor, media);

            this.on('start', this, this.proxy('started'));
            this.on('save', this, this.proxy('saved'));
        },
        started: function (holder) {
            if (!this.media) {
                var selection = this.editor.getSelection();
                this.media = selection && selection.getSelectedElement();
            }

            var el = this.media;
            if (!el || !el.is('img')) {
                return;
            }
            holder.url = el.getAttribute('src');
        },
        saved: function (data) {
            var element, editor = this.editor;
            if (!(element = this.media)) {
                element = editor.document.createElement('img');
                element.addClass('img');
                element.addClass('img-responsive');
                // focus event handler interactions between bootstrap (modal)
                // and ckeditor (RTE) lead to blowing the stack in Safari and
                // Chrome (but not FF) when this is done synchronously =>
                // defer insertion so modal has been hidden & destroyed before
                // it happens
                setTimeout(function () {
                    editor.insertElement(element);
                }, 0);
            }

            var style = data.style;
            element.setAttribute('src', data.url);
            element.removeAttribute('data-cke-saved-src');
            if (style) { element.addClass(style); }
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
            return element.data('oe-model') === 'ir.ui.view';
        });
        if (!viewRoot) { return null; }
        // if viewRoot is the first link, don't edit it.
        return new CKEDITOR.dom.elementPath(commonAncestor, viewRoot)
                .contains('a', true);
    }

    website.editor.FontIconsDialog = website.editor.Media.extend({
        template: 'website.editor.dialog.font-icons',
        events : _.extend({}, website.editor.Dialog.prototype.events, {
            change: 'update_preview',
            'click .font-icons-icon': function (e) {
                e.preventDefault();
                e.stopPropagation();

                this.$('#fa-icon').val(e.target.getAttribute('data-id'));
                this.update_preview();
            },
            'click #fa-preview span': function (e) {
                e.preventDefault();
                e.stopPropagation();

                this.$('#fa-size').val(e.target.getAttribute('data-size'));
                this.update_preview();
            },
        }),

        // List of FontAwesome icons in 4.0.3, extracted from the cheatsheet.
        // Each icon provides the unicode codepoint as ``text`` and the class
        // name as ``id`` so the whole thing can be fed directly to select2
        // without post-processing and do the right thing (except for the part
        // where we still need to implement ``initSelection``)
        // TODO: add id/name to the text in order to allow FAYT selection of icons?
        icons: [{"text": "\uf000", "id": "fa-glass"}, {"text": "\uf001", "id": "fa-music"}, {"text": "\uf002", "id": "fa-search"}, {"text": "\uf003", "id": "fa-envelope-o"}, {"text": "\uf004", "id": "fa-heart"}, {"text": "\uf005", "id": "fa-star"}, {"text": "\uf006", "id": "fa-star-o"}, {"text": "\uf007", "id": "fa-user"}, {"text": "\uf008", "id": "fa-film"}, {"text": "\uf009", "id": "fa-th-large"}, {"text": "\uf00a", "id": "fa-th"}, {"text": "\uf00b", "id": "fa-th-list"}, {"text": "\uf00c", "id": "fa-check"}, {"text": "\uf00d", "id": "fa-times"}, {"text": "\uf00e", "id": "fa-search-plus"}, {"text": "\uf010", "id": "fa-search-minus"}, {"text": "\uf011", "id": "fa-power-off"}, {"text": "\uf012", "id": "fa-signal"}, {"text": "\uf013", "id": "fa-cog"}, {"text": "\uf014", "id": "fa-trash-o"}, {"text": "\uf015", "id": "fa-home"}, {"text": "\uf016", "id": "fa-file-o"}, {"text": "\uf017", "id": "fa-clock-o"}, {"text": "\uf018", "id": "fa-road"}, {"text": "\uf019", "id": "fa-download"}, {"text": "\uf01a", "id": "fa-arrow-circle-o-down"}, {"text": "\uf01b", "id": "fa-arrow-circle-o-up"}, {"text": "\uf01c", "id": "fa-inbox"}, {"text": "\uf01d", "id": "fa-play-circle-o"}, {"text": "\uf01e", "id": "fa-repeat"}, {"text": "\uf021", "id": "fa-refresh"}, {"text": "\uf022", "id": "fa-list-alt"}, {"text": "\uf023", "id": "fa-lock"}, {"text": "\uf024", "id": "fa-flag"}, {"text": "\uf025", "id": "fa-headphones"}, {"text": "\uf026", "id": "fa-volume-off"}, {"text": "\uf027", "id": "fa-volume-down"}, {"text": "\uf028", "id": "fa-volume-up"}, {"text": "\uf029", "id": "fa-qrcode"}, {"text": "\uf02a", "id": "fa-barcode"}, {"text": "\uf02b", "id": "fa-tag"}, {"text": "\uf02c", "id": "fa-tags"}, {"text": "\uf02d", "id": "fa-book"}, {"text": "\uf02e", "id": "fa-bookmark"}, {"text": "\uf02f", "id": "fa-print"}, {"text": "\uf030", "id": "fa-camera"}, {"text": "\uf031", "id": "fa-font"}, {"text": "\uf032", "id": "fa-bold"}, {"text": "\uf033", "id": "fa-italic"}, {"text": "\uf034", "id": "fa-text-height"}, {"text": "\uf035", "id": "fa-text-width"}, {"text": "\uf036", "id": "fa-align-left"}, {"text": "\uf037", "id": "fa-align-center"}, {"text": "\uf038", "id": "fa-align-right"}, {"text": "\uf039", "id": "fa-align-justify"}, {"text": "\uf03a", "id": "fa-list"}, {"text": "\uf03b", "id": "fa-outdent"}, {"text": "\uf03c", "id": "fa-indent"}, {"text": "\uf03d", "id": "fa-video-camera"}, {"text": "\uf03e", "id": "fa-picture-o"}, {"text": "\uf040", "id": "fa-pencil"}, {"text": "\uf041", "id": "fa-map-marker"}, {"text": "\uf042", "id": "fa-adjust"}, {"text": "\uf043", "id": "fa-tint"}, {"text": "\uf044", "id": "fa-pencil-square-o"}, {"text": "\uf045", "id": "fa-share-square-o"}, {"text": "\uf046", "id": "fa-check-square-o"}, {"text": "\uf047", "id": "fa-arrows"}, {"text": "\uf048", "id": "fa-step-backward"}, {"text": "\uf049", "id": "fa-fast-backward"}, {"text": "\uf04a", "id": "fa-backward"}, {"text": "\uf04b", "id": "fa-play"}, {"text": "\uf04c", "id": "fa-pause"}, {"text": "\uf04d", "id": "fa-stop"}, {"text": "\uf04e", "id": "fa-forward"}, {"text": "\uf050", "id": "fa-fast-forward"}, {"text": "\uf051", "id": "fa-step-forward"}, {"text": "\uf052", "id": "fa-eject"}, {"text": "\uf053", "id": "fa-chevron-left"}, {"text": "\uf054", "id": "fa-chevron-right"}, {"text": "\uf055", "id": "fa-plus-circle"}, {"text": "\uf056", "id": "fa-minus-circle"}, {"text": "\uf057", "id": "fa-times-circle"}, {"text": "\uf058", "id": "fa-check-circle"}, {"text": "\uf059", "id": "fa-question-circle"}, {"text": "\uf05a", "id": "fa-info-circle"}, {"text": "\uf05b", "id": "fa-crosshairs"}, {"text": "\uf05c", "id": "fa-times-circle-o"}, {"text": "\uf05d", "id": "fa-check-circle-o"}, {"text": "\uf05e", "id": "fa-ban"}, {"text": "\uf060", "id": "fa-arrow-left"}, {"text": "\uf061", "id": "fa-arrow-right"}, {"text": "\uf062", "id": "fa-arrow-up"}, {"text": "\uf063", "id": "fa-arrow-down"}, {"text": "\uf064", "id": "fa-share"}, {"text": "\uf065", "id": "fa-expand"}, {"text": "\uf066", "id": "fa-compress"}, {"text": "\uf067", "id": "fa-plus"}, {"text": "\uf068", "id": "fa-minus"}, {"text": "\uf069", "id": "fa-asterisk"}, {"text": "\uf06a", "id": "fa-exclamation-circle"}, {"text": "\uf06b", "id": "fa-gift"}, {"text": "\uf06c", "id": "fa-leaf"}, {"text": "\uf06d", "id": "fa-fire"}, {"text": "\uf06e", "id": "fa-eye"}, {"text": "\uf070", "id": "fa-eye-slash"}, {"text": "\uf071", "id": "fa-exclamation-triangle"}, {"text": "\uf072", "id": "fa-plane"}, {"text": "\uf073", "id": "fa-calendar"}, {"text": "\uf074", "id": "fa-random"}, {"text": "\uf075", "id": "fa-comment"}, {"text": "\uf076", "id": "fa-magnet"}, {"text": "\uf077", "id": "fa-chevron-up"}, {"text": "\uf078", "id": "fa-chevron-down"}, {"text": "\uf079", "id": "fa-retweet"}, {"text": "\uf07a", "id": "fa-shopping-cart"}, {"text": "\uf07b", "id": "fa-folder"}, {"text": "\uf07c", "id": "fa-folder-open"}, {"text": "\uf07d", "id": "fa-arrows-v"}, {"text": "\uf07e", "id": "fa-arrows-h"}, {"text": "\uf080", "id": "fa-bar-chart-o"}, {"text": "\uf081", "id": "fa-twitter-square"}, {"text": "\uf082", "id": "fa-facebook-square"}, {"text": "\uf083", "id": "fa-camera-retro"}, {"text": "\uf084", "id": "fa-key"}, {"text": "\uf085", "id": "fa-cogs"}, {"text": "\uf086", "id": "fa-comments"}, {"text": "\uf087", "id": "fa-thumbs-o-up"}, {"text": "\uf088", "id": "fa-thumbs-o-down"}, {"text": "\uf089", "id": "fa-star-half"}, {"text": "\uf08a", "id": "fa-heart-o"}, {"text": "\uf08b", "id": "fa-sign-out"}, {"text": "\uf08c", "id": "fa-linkedin-square"}, {"text": "\uf08d", "id": "fa-thumb-tack"}, {"text": "\uf08e", "id": "fa-external-link"}, {"text": "\uf090", "id": "fa-sign-in"}, {"text": "\uf091", "id": "fa-trophy"}, {"text": "\uf092", "id": "fa-github-square"}, {"text": "\uf093", "id": "fa-upload"}, {"text": "\uf094", "id": "fa-lemon-o"}, {"text": "\uf095", "id": "fa-phone"}, {"text": "\uf096", "id": "fa-square-o"}, {"text": "\uf097", "id": "fa-bookmark-o"}, {"text": "\uf098", "id": "fa-phone-square"}, {"text": "\uf099", "id": "fa-twitter"}, {"text": "\uf09a", "id": "fa-facebook"}, {"text": "\uf09b", "id": "fa-github"}, {"text": "\uf09c", "id": "fa-unlock"}, {"text": "\uf09d", "id": "fa-credit-card"}, {"text": "\uf09e", "id": "fa-rss"}, {"text": "\uf0a0", "id": "fa-hdd-o"}, {"text": "\uf0a1", "id": "fa-bullhorn"}, {"text": "\uf0f3", "id": "fa-bell"}, {"text": "\uf0a3", "id": "fa-certificate"}, {"text": "\uf0a4", "id": "fa-hand-o-right"}, {"text": "\uf0a5", "id": "fa-hand-o-left"}, {"text": "\uf0a6", "id": "fa-hand-o-up"}, {"text": "\uf0a7", "id": "fa-hand-o-down"}, {"text": "\uf0a8", "id": "fa-arrow-circle-left"}, {"text": "\uf0a9", "id": "fa-arrow-circle-right"}, {"text": "\uf0aa", "id": "fa-arrow-circle-up"}, {"text": "\uf0ab", "id": "fa-arrow-circle-down"}, {"text": "\uf0ac", "id": "fa-globe"}, {"text": "\uf0ad", "id": "fa-wrench"}, {"text": "\uf0ae", "id": "fa-tasks"}, {"text": "\uf0b0", "id": "fa-filter"}, {"text": "\uf0b1", "id": "fa-briefcase"}, {"text": "\uf0b2", "id": "fa-arrows-alt"}, {"text": "\uf0c0", "id": "fa-users"}, {"text": "\uf0c1", "id": "fa-link"}, {"text": "\uf0c2", "id": "fa-cloud"}, {"text": "\uf0c3", "id": "fa-flask"}, {"text": "\uf0c4", "id": "fa-scissors"}, {"text": "\uf0c5", "id": "fa-files-o"}, {"text": "\uf0c6", "id": "fa-paperclip"}, {"text": "\uf0c7", "id": "fa-floppy-o"}, {"text": "\uf0c8", "id": "fa-square"}, {"text": "\uf0c9", "id": "fa-bars"}, {"text": "\uf0ca", "id": "fa-list-ul"}, {"text": "\uf0cb", "id": "fa-list-ol"}, {"text": "\uf0cc", "id": "fa-strikethrough"}, {"text": "\uf0cd", "id": "fa-underline"}, {"text": "\uf0ce", "id": "fa-table"}, {"text": "\uf0d0", "id": "fa-magic"}, {"text": "\uf0d1", "id": "fa-truck"}, {"text": "\uf0d2", "id": "fa-pinterest"}, {"text": "\uf0d3", "id": "fa-pinterest-square"}, {"text": "\uf0d4", "id": "fa-google-plus-square"}, {"text": "\uf0d5", "id": "fa-google-plus"}, {"text": "\uf0d6", "id": "fa-money"}, {"text": "\uf0d7", "id": "fa-caret-down"}, {"text": "\uf0d8", "id": "fa-caret-up"}, {"text": "\uf0d9", "id": "fa-caret-left"}, {"text": "\uf0da", "id": "fa-caret-right"}, {"text": "\uf0db", "id": "fa-columns"}, {"text": "\uf0dc", "id": "fa-sort"}, {"text": "\uf0dd", "id": "fa-sort-asc"}, {"text": "\uf0de", "id": "fa-sort-desc"}, {"text": "\uf0e0", "id": "fa-envelope"}, {"text": "\uf0e1", "id": "fa-linkedin"}, {"text": "\uf0e2", "id": "fa-undo"}, {"text": "\uf0e3", "id": "fa-gavel"}, {"text": "\uf0e4", "id": "fa-tachometer"}, {"text": "\uf0e5", "id": "fa-comment-o"}, {"text": "\uf0e6", "id": "fa-comments-o"}, {"text": "\uf0e7", "id": "fa-bolt"}, {"text": "\uf0e8", "id": "fa-sitemap"}, {"text": "\uf0e9", "id": "fa-umbrella"}, {"text": "\uf0ea", "id": "fa-clipboard"}, {"text": "\uf0eb", "id": "fa-lightbulb-o"}, {"text": "\uf0ec", "id": "fa-exchange"}, {"text": "\uf0ed", "id": "fa-cloud-download"}, {"text": "\uf0ee", "id": "fa-cloud-upload"}, {"text": "\uf0f0", "id": "fa-user-md"}, {"text": "\uf0f1", "id": "fa-stethoscope"}, {"text": "\uf0f2", "id": "fa-suitcase"}, {"text": "\uf0a2", "id": "fa-bell-o"}, {"text": "\uf0f4", "id": "fa-coffee"}, {"text": "\uf0f5", "id": "fa-cutlery"}, {"text": "\uf0f6", "id": "fa-file-text-o"}, {"text": "\uf0f7", "id": "fa-building-o"}, {"text": "\uf0f8", "id": "fa-hospital-o"}, {"text": "\uf0f9", "id": "fa-ambulance"}, {"text": "\uf0fa", "id": "fa-medkit"}, {"text": "\uf0fb", "id": "fa-fighter-jet"}, {"text": "\uf0fc", "id": "fa-beer"}, {"text": "\uf0fd", "id": "fa-h-square"}, {"text": "\uf0fe", "id": "fa-plus-square"}, {"text": "\uf100", "id": "fa-angle-double-left"}, {"text": "\uf101", "id": "fa-angle-double-right"}, {"text": "\uf102", "id": "fa-angle-double-up"}, {"text": "\uf103", "id": "fa-angle-double-down"}, {"text": "\uf104", "id": "fa-angle-left"}, {"text": "\uf105", "id": "fa-angle-right"}, {"text": "\uf106", "id": "fa-angle-up"}, {"text": "\uf107", "id": "fa-angle-down"}, {"text": "\uf108", "id": "fa-desktop"}, {"text": "\uf109", "id": "fa-laptop"}, {"text": "\uf10a", "id": "fa-tablet"}, {"text": "\uf10b", "id": "fa-mobile"}, {"text": "\uf10c", "id": "fa-circle-o"}, {"text": "\uf10d", "id": "fa-quote-left"}, {"text": "\uf10e", "id": "fa-quote-right"}, {"text": "\uf110", "id": "fa-spinner"}, {"text": "\uf111", "id": "fa-circle"}, {"text": "\uf112", "id": "fa-reply"}, {"text": "\uf113", "id": "fa-github-alt"}, {"text": "\uf114", "id": "fa-folder-o"}, {"text": "\uf115", "id": "fa-folder-open-o"}, {"text": "\uf118", "id": "fa-smile-o"}, {"text": "\uf119", "id": "fa-frown-o"}, {"text": "\uf11a", "id": "fa-meh-o"}, {"text": "\uf11b", "id": "fa-gamepad"}, {"text": "\uf11c", "id": "fa-keyboard-o"}, {"text": "\uf11d", "id": "fa-flag-o"}, {"text": "\uf11e", "id": "fa-flag-checkered"}, {"text": "\uf120", "id": "fa-terminal"}, {"text": "\uf121", "id": "fa-code"}, {"text": "\uf122", "id": "fa-reply-all"}, {"text": "\uf122", "id": "fa-mail-reply-all"}, {"text": "\uf123", "id": "fa-star-half-o"}, {"text": "\uf124", "id": "fa-location-arrow"}, {"text": "\uf125", "id": "fa-crop"}, {"text": "\uf126", "id": "fa-code-fork"}, {"text": "\uf127", "id": "fa-chain-broken"}, {"text": "\uf128", "id": "fa-question"}, {"text": "\uf129", "id": "fa-info"}, {"text": "\uf12a", "id": "fa-exclamation"}, {"text": "\uf12b", "id": "fa-superscript"}, {"text": "\uf12c", "id": "fa-subscript"}, {"text": "\uf12d", "id": "fa-eraser"}, {"text": "\uf12e", "id": "fa-puzzle-piece"}, {"text": "\uf130", "id": "fa-microphone"}, {"text": "\uf131", "id": "fa-microphone-slash"}, {"text": "\uf132", "id": "fa-shield"}, {"text": "\uf133", "id": "fa-calendar-o"}, {"text": "\uf134", "id": "fa-fire-extinguisher"}, {"text": "\uf135", "id": "fa-rocket"}, {"text": "\uf136", "id": "fa-maxcdn"}, {"text": "\uf137", "id": "fa-chevron-circle-left"}, {"text": "\uf138", "id": "fa-chevron-circle-right"}, {"text": "\uf139", "id": "fa-chevron-circle-up"}, {"text": "\uf13a", "id": "fa-chevron-circle-down"}, {"text": "\uf13b", "id": "fa-html5"}, {"text": "\uf13c", "id": "fa-css3"}, {"text": "\uf13d", "id": "fa-anchor"}, {"text": "\uf13e", "id": "fa-unlock-alt"}, {"text": "\uf140", "id": "fa-bullseye"}, {"text": "\uf141", "id": "fa-ellipsis-h"}, {"text": "\uf142", "id": "fa-ellipsis-v"}, {"text": "\uf143", "id": "fa-rss-square"}, {"text": "\uf144", "id": "fa-play-circle"}, {"text": "\uf145", "id": "fa-ticket"}, {"text": "\uf146", "id": "fa-minus-square"}, {"text": "\uf147", "id": "fa-minus-square-o"}, {"text": "\uf148", "id": "fa-level-up"}, {"text": "\uf149", "id": "fa-level-down"}, {"text": "\uf14a", "id": "fa-check-square"}, {"text": "\uf14b", "id": "fa-pencil-square"}, {"text": "\uf14c", "id": "fa-external-link-square"}, {"text": "\uf14d", "id": "fa-share-square"}, {"text": "\uf14e", "id": "fa-compass"}, {"text": "\uf150", "id": "fa-caret-square-o-down"}, {"text": "\uf151", "id": "fa-caret-square-o-up"}, {"text": "\uf152", "id": "fa-caret-square-o-right"}, {"text": "\uf153", "id": "fa-eur"}, {"text": "\uf154", "id": "fa-gbp"}, {"text": "\uf155", "id": "fa-usd"}, {"text": "\uf156", "id": "fa-inr"}, {"text": "\uf157", "id": "fa-jpy"}, {"text": "\uf158", "id": "fa-rub"}, {"text": "\uf159", "id": "fa-krw"}, {"text": "\uf15a", "id": "fa-btc"}, {"text": "\uf15b", "id": "fa-file"}, {"text": "\uf15c", "id": "fa-file-text"}, {"text": "\uf15d", "id": "fa-sort-alpha-asc"}, {"text": "\uf15e", "id": "fa-sort-alpha-desc"}, {"text": "\uf160", "id": "fa-sort-amount-asc"}, {"text": "\uf161", "id": "fa-sort-amount-desc"}, {"text": "\uf162", "id": "fa-sort-numeric-asc"}, {"text": "\uf163", "id": "fa-sort-numeric-desc"}, {"text": "\uf164", "id": "fa-thumbs-up"}, {"text": "\uf165", "id": "fa-thumbs-down"}, {"text": "\uf166", "id": "fa-youtube-square"}, {"text": "\uf167", "id": "fa-youtube"}, {"text": "\uf168", "id": "fa-xing"}, {"text": "\uf169", "id": "fa-xing-square"}, {"text": "\uf16a", "id": "fa-youtube-play"}, {"text": "\uf16b", "id": "fa-dropbox"}, {"text": "\uf16c", "id": "fa-stack-overflow"}, {"text": "\uf16d", "id": "fa-instagram"}, {"text": "\uf16e", "id": "fa-flickr"}, {"text": "\uf170", "id": "fa-adn"}, {"text": "\uf171", "id": "fa-bitbucket"}, {"text": "\uf172", "id": "fa-bitbucket-square"}, {"text": "\uf173", "id": "fa-tumblr"}, {"text": "\uf174", "id": "fa-tumblr-square"}, {"text": "\uf175", "id": "fa-long-arrow-down"}, {"text": "\uf176", "id": "fa-long-arrow-up"}, {"text": "\uf177", "id": "fa-long-arrow-left"}, {"text": "\uf178", "id": "fa-long-arrow-right"}, {"text": "\uf179", "id": "fa-apple"}, {"text": "\uf17a", "id": "fa-windows"}, {"text": "\uf17b", "id": "fa-android"}, {"text": "\uf17c", "id": "fa-linux"}, {"text": "\uf17d", "id": "fa-dribbble"}, {"text": "\uf17e", "id": "fa-skype"}, {"text": "\uf180", "id": "fa-foursquare"}, {"text": "\uf181", "id": "fa-trello"}, {"text": "\uf182", "id": "fa-female"}, {"text": "\uf183", "id": "fa-male"}, {"text": "\uf184", "id": "fa-gittip"}, {"text": "\uf185", "id": "fa-sun-o"}, {"text": "\uf186", "id": "fa-moon-o"}, {"text": "\uf187", "id": "fa-archive"}, {"text": "\uf188", "id": "fa-bug"}, {"text": "\uf189", "id": "fa-vk"}, {"text": "\uf18a", "id": "fa-weibo"}, {"text": "\uf18b", "id": "fa-renren"}, {"text": "\uf18c", "id": "fa-pagelines"}, {"text": "\uf18d", "id": "fa-stack-exchange"}, {"text": "\uf18e", "id": "fa-arrow-circle-o-right"}, {"text": "\uf190", "id": "fa-arrow-circle-o-left"}, {"text": "\uf191", "id": "fa-caret-square-o-left"}, {"text": "\uf192", "id": "fa-dot-circle-o"}, {"text": "\uf193", "id": "fa-wheelchair"}, {"text": "\uf194", "id": "fa-vimeo-square"}, {"text": "\uf195", "id": "fa-try"}, {"text": "\uf196", "id": "fa-plus-square-o"}],
        /**
         * Initializes select2: in Chrome and Safari, <select> font apparently
         * isn't customizable (?) and the fontawesome glyphs fail to appear.
         */
        start: function () {
            return this._super().then(this.proxy('load_data'));
        },
        search: function (needle) {
            var icons = this.icons;
            if (needle) {
                icons = _(icons).filter(function (icon) {
                    return icon.id.substring(3).indexOf(needle) !== -1;
                });
            }

            this.$('div.font-icons-icons').html(
                openerp.qweb.render(
                    'website.editor.dialog.font-icons.icons',
                    {icons: icons}));
        },
        /**
         * Removes existing FontAwesome classes on the bound element, and sets
         * all the new ones if necessary.
         */
        save: function () {
            var style = this.media.$.attributes.style ? this.media.$.attributes.style.textContent : '';
            var classes = (this.media.$.className||"").split(/\s+/);
            var non_fa_classes = _.reject(classes, function (cls) {
                return cls === 'fa' || /^fa-/.test(cls);
            });
            var final_classes = non_fa_classes.concat(this.get_fa_classes());
            this.media.$.className = final_classes.join(' ');
            this.media.renameNode("span");
            this.media.$.attributes.style.textContent = style;
            this._super();
        },
        /**
         * Looks up the various FontAwesome classes on the bound element and
         * sets the corresponding template/form elements to the right state.
         * If multiple classes of the same category are present on an element
         * (e.g. fa-lg and fa-3x) the last one occurring will be selected,
         * which may not match the visual look of the element.
         */
        load_data: function () {
            var classes = (this.media&&this.media.$.className||"").split(/\s+/);
            for (var i = 0; i < classes.length; i++) {
                var cls = classes[i];
                switch(cls) {
                case 'fa-2x':case 'fa-3x':case 'fa-4x':case 'fa-5x':
                    // size classes
                    this.$('#fa-size').val(cls);
                    continue;
                case 'fa-spin':
                case 'fa-rotate-90':case 'fa-rotate-180':case 'fa-rotate-270':
                case 'fa-flip-horizontal':case 'fa-rotate-vertical':
                    this.$('#fa-rotation').val(cls);
                    continue;
                case 'fa-fw':
                    continue;
                case 'fa-border':
                    this.$('#fa-border').prop('checked', true);
                    continue;
                default:
                    if (!/^fa-/.test(cls)) { continue; }
                    this.$('#fa-icon').val(cls);
                }
            }
            this.update_preview();
        },
        /**
         * Serializes the dialog to an array of FontAwesome classes. Includes
         * the base ``fa``.
         */
        get_fa_classes: function () {
            return [
                'fa',
                this.$('#fa-icon').val(),
                this.$('#fa-size').val(),
                this.$('#fa-rotation').val(),
                this.$('#fa-border').prop('checked') ? 'fa-border' : ''
            ];
        },
        update_preview: function () {
            this.$preview.empty();
            var $preview = this.$('#fa-preview').empty();

            var sizes = ['', 'fa-2x', 'fa-3x', 'fa-4x', 'fa-5x'];
            var classes = this.get_fa_classes();
            var no_sizes = _.difference(classes, sizes).join(' ');
            var selected = false;
            for (var i = sizes.length - 1; i >= 0; i--) {
                var size = sizes[i];

                var $p = $('<span>')
                        .attr('data-size', size)
                        .addClass(size)
                        .addClass(no_sizes);

                if ((size && _.contains(classes, size)) || (size === "" && !selected)) {
                    this.$preview.append($p.clone());
                    this.$('#fa-size').val(size);
                    $p.addClass('font-icons-selected');
                    selected = true;
                }
                $preview.prepend($p);
            }
        },
        clear: function () {
            this.media.$.className = this.media.$.className.replace(/(^|\s)(fa(\s|$)|fa-[^\s]*)/g, ' ');
        },
    });

    website.editor.VideoDialog = website.editor.Media.extend({
        template: 'website.editor.dialog.video',
        events : _.extend({}, website.editor.Dialog.prototype.events, {
            'click input#urlvideo ~ button': 'get_video',
            'click input#embedvideo ~ button': 'get_embed_video',
            'change input#urlvideo': 'change_input',
            'keyup input#urlvideo': 'change_input',
            'change input#embedvideo': 'change_input',
            'keyup input#embedvideo': 'change_input'
        }),
        start: function () {
            this.$iframe = this.$("iframe");
            var $media = $(this.media && this.media.$);
            if ($media.hasClass("media_iframe_video")) {
                var src = $media.data('src');
                this.$("input#urlvideo").val(src);
                this.$("#autoplay").attr("checked", src.indexOf('autoplay=1') != -1);
                this.get_video();
            }
            return this._super();
        },
        change_input: function (e) {
            var $input = $(e.target);
            var $button = $input.parent().find("button");
            if ($input.val() === "") {
                $button.addClass("btn-default").removeClass("btn-primary");
            } else {
                $button.removeClass("btn-default").addClass("btn-primary");
            }
        },
        get_url: function () {
            var video_id = this.$("#video_id").val();
            var video_type = this.$("#video_type").val();
            switch (video_type) {
                case "youtube":
                    return "//www.youtube.com/embed/" + video_id + "?autoplay=" + (this.$("#autoplay").is(":checked") ? 1 : 0);
                case "vimeo":
                    return "//player.vimeo.com/video/" + video_id + "?autoplay=" + (this.$("#autoplay").is(":checked") ? 1 : 0);
                case "dailymotion":
                    return "//www.dailymotion.com/embed/video/" + video_id + "?autoplay=" + (this.$("#autoplay").is(":checked") ? 1 : 0);
                default:
                    return video_id;
            }
        },
        get_embed_video: function (event) {
            event.preventDefault();
            var embedvideo = this.$("input#embedvideo").val().match(/src=["']?([^"']+)["' ]?/);
            if (embedvideo) {
                this.$("input#urlvideo").val(embedvideo[1]);
                this.get_video(event);
            }
            return false;
        },
        get_video: function (event) {
            if (event) event.preventDefault();
            var needle = this.$("input#urlvideo").val();
            var video_id;
            var video_type;

            if (needle.indexOf(".youtube.") != -1) {
                video_type = "youtube";
                video_id = needle.match(/\.youtube\.[a-z]+\/(embed\/|watch\?v=)?([^\/?&]+)/i)[2];
            } else if (needle.indexOf("//youtu.") != -1) {
                video_type = "youtube";
                video_id = needle.match(/youtube\.[a-z]+\/([^\/?&]+)/i)[1];
            } else if (needle.indexOf("player.vimeo.") != -1 || needle.indexOf("//vimeo.") != -1) {
                video_type = "vimeo";
                video_id = needle.match(/vimeo\.[a-z]+\/(video\/)?([^?&]+)/i)[2];
            } else if (needle.indexOf(".dailymotion.") != -1) {
                video_type = "dailymotion";
                video_id = needle.match(/dailymotion\.[a-z]+\/(embed\/)?(video\/)?([^\/?&]+)/i)[3];
            } else {
                video_type = "";
                video_id = needle;
            }

            this.$("#video_id").val(video_id);
            this.$("#video_type").val(video_type);

            this.$iframe.attr("src", this.get_url());
            return false;
        },
        save: function () {
            var video_id = this.$("#video_id").val();
            if (!video_id) {
                this.$("button.btn-primary").click();
                video_id = this.$("#video_id").val();
            }
            var video_type = this.$("#video_type").val();
            var style = this.media.$.attributes.style ? this.media.$.attributes.style.textContent : '';
            var $iframe = $(
                '<div class="media_iframe_video" data-src="'+this.get_url()+'" style="'+style+'">'+
                    '<div class="css_editable_mode_display">&nbsp;</div>'+
                    '<iframe src="'+this.get_url()+'" frameborder="0" allowfullscreen="allowfullscreen"></iframe>'+
                '</div>');
            $(this.media.$).replaceWith($iframe);
            this.media.$ = $iframe[0];
            this._super();
        },
        clear: function () {
            delete this.media.$.dataset.src;
            this.media.$.className = this.media.$.className.replace(/(^|\s)media_iframe_video(\s|$)/g, ' ');
        },
    });

    website.Observer = window.MutationObserver || window.WebkitMutationObserver || window.JsMutationObserver;
    var OBSERVER_CONFIG = {
        childList: true,
        attributes: true,
        characterData: true,
        subtree: true,
        attributeOldValue: true,
    };
    var observer = new website.Observer(function (mutations) {
        // NOTE: Webkit does not fire DOMAttrModified => webkit browsers
        //       relying on JsMutationObserver shim (Chrome < 18, Safari < 6)
        //       will not mark dirty on attribute changes (@class, img/@src,
        //       a/@href, ...)
        _(mutations).chain()
            .filter(function (m) {
                // ignore any SVG target, these blokes are like weird mon
                if (m.target && m.target instanceof SVGElement) {
                    return false;
                }

                // ignore any change related to mundane image-edit-button
                if (m.target && m.target.className
                        && m.target.className.indexOf('image-edit-button') !== -1) {
                    return false;
                }
                switch(m.type) {
                case 'attributes':
                    // ignore special attributes and .cke_focus class being added or removed
                    var ignored_attrs = ['id', 'contenteditable', 'attributeeditable']
                    if (_.contains(ignored_attrs, m.attributeName)) { return false; }
                    // if attribute is not a class, can't be .cke_focus change
                    if (m.attributeName !== 'class') { return true; }

                    // find out what classes were added or removed
                    var oldClasses = (m.oldValue || '').split(/\s+/);
                    var newClasses = m.target.className.split(/\s+/);
                    var change = _.union(_.difference(oldClasses, newClasses),
                                         _.difference(newClasses, oldClasses));
                    // ignore mutation if the *only* change is .cke_focus
                    return change.length !== 1 || change[0] === 'cke_focus';
                case 'childList':
                    setTimeout(function () {
                        fixup_browser_crap(m.addedNodes);
                    }, 0);
                    // Remove ignorable nodes from addedNodes or removedNodes,
                    // if either set remains non-empty it's considered to be an
                    // impactful change. Otherwise it's ignored.
                    return !!remove_mundane_nodes(m.addedNodes).length ||
                           !!remove_mundane_nodes(m.removedNodes).length;
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
    function remove_mundane_nodes(nodes) {
        if (!nodes || !nodes.length) { return []; }

        var output = [];
        for(var i=0; i<nodes.length; ++i) {
            var node = nodes[i];
            if (node.nodeType === document.ELEMENT_NODE) {
                if (node.nodeName === 'BR' && node.getAttribute('type') === '_moz') {
                    // <br type="_moz"> appears when focusing RTE in FF, ignore
                    continue;
                } else if (node.nodeName === 'DIV' && $(node).hasClass('oe_drop_zone')) {
                    // ignore dropzone inserted by snippets
                    continue
                }
            }

            output.push(node);
        }
        return output;
    }

    var programmatic_styles = {
        float: 1,
        display: 1,
        position: 1,
        top: 1,
        left: 1,
        right: 1,
        bottom: 1,
    };
    function fixup_browser_crap(nodes) {
        if (!nodes || !nodes.length) { return; }
        /**
         * Checks that the node only has a @style, not e.g. @class or whatever
         */
        function has_only_style(node) {
            for (var i = 0; i < node.attributes.length; i++) {
                var attr = node.attributes[i];
                if (attr.attributeName !== 'style') {
                    return false;
                }
            }
            return true;
        }
        function has_programmatic_style(node) {
            for (var i = 0; i < node.style.length; i++) {
              var style = node.style[i];
              if (programmatic_styles[style]) {
                  return true;
              }
            }
            return false;
        }

        for (var i=0; i<nodes.length; ++i) {
            var node = nodes[i];
            if (node.nodeType !== document.ELEMENT_NODE) { continue; }

            if (node.nodeName === 'SPAN'
                    && has_only_style(node)
                    && !has_programmatic_style(node)) {
                // On backspace, webkit browsers create a <span> with a bunch of
                // inline styles "remembering" where they come from. Refs:
                //    http://www.neotericdesign.com/blog/2013/3/working-around-chrome-s-contenteditable-span-bug
                //    https://code.google.com/p/chromium/issues/detail?id=226941
                //    https://bugs.webkit.org/show_bug.cgi?id=114791
                //    http://dev.ckeditor.com/ticket/9998
                var child, parent = node.parentNode;
                while (child = node.firstChild) {
                    parent.insertBefore(child, node);
                }
                parent.removeChild(node);
                // chances are we had e.g.
                //  <p>foo</p>
                //  <p>bar</p>
                // merged the lines getting this in webkit
                //  <p>foo<span>bar</span></p>
                // after unwrapping the span, we have 2 text nodes
                //  <p>[foo][bar]</p>
                // where we probably want only one. Normalize will merge
                // adjacent text nodes. However, does not merge text and cdata
                parent.normalize();
            }
        }
    }
})();
