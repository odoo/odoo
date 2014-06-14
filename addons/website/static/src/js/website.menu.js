(function () {
    'use strict';
    
    var website = openerp.website;
    var _t = openerp._t;

    website.Menu =  openerp.Widget.extend({
        mobilePreview: function () {
            (new website.MobilePreview()).appendTo($(document.body));
        },
        launchSeo: function () {
            (new website.seo.Configurator(this)).appendTo($(document.body));
        },
        unflow: function() {
            self.reflow('all_inside');
        },
        // reflow: function() {
        //     var self = this;
        //     var $more_container = this.$('#menu_more_container').hide();
        //     var $more = this.$('#menu_more');
        //     var $websitetopview = this.$el.find('#website-top-view li');
        //     $more.children('li').insertBefore($more_container);
        //     var $toplevel_items = this.$el.find('li').not($websitetopview).not($more_container).hide();
        //     $toplevel_items.each(function() {
        //         var remaining_space = self.$el.parent().width() - $more_container.outerWidth() - 50;
        //         self.$el.children(':visible').each(function() {
        //             remaining_space -= $(this).outerWidth();
        //         });

        //         if ($(this).width() > remaining_space) {
        //             return false;
        //         }
        //         $(this).show();
        //     });
        //     $more.append($toplevel_items.filter(':hidden').show());
        //     $more_container.toggle(!!$more.children().length);
        //     // Hide toplevel item if there is only one
        //     var $toplevel = this.$el.children("li:visible");
        //     if ($toplevel.length === 1) {
        //         $toplevel.hide();
        //     }
        // },
        reflow: function(behavior) {
            var self = this;
            var $more_container = this.$('#menu_more_container').hide();
            var $more = this.$('#menu_more');
            var $systray = this.$el.parents().find('.oe_systray');

            $more.children('li').insertBefore($more_container);  // Pull all the items out the more menu
            
            // All outside more displau all the items, hide the more menu and exit
            if (behavior === 'all_outside') {
                this.$el.find('li').show();
                $more_container.hide();
                return;
            }

            var $toplevel_items = this.$el.find('li').not($more_container).not($systray.find('li')).hide();
            $toplevel_items.each(function() {
                // In all inside mode, we do not compute to know if we must hide the items, we hide them all
                if (behavior === 'all_inside') {
                    return false;
                }
                var remaining_space = self.$el.parent().width() - $more_container.outerWidth();
                self.$el.parent().children(':visible').each(function() {
                    remaining_space -= $(this).outerWidth();
                });

                if ($(this).width() > remaining_space) {
                    return false;
                }
                $(this).show();
            });
            $more.append($toplevel_items.filter(':hidden').show());
            $more_container.toggle(!!$more.children().length || behavior === 'all_inside');
            // Hide toplevel item if there is only one
            var $toplevel = this.$el.children("li:visible");
            if ($toplevel.length === 1 && behavior != 'all_inside') {
                $toplevel.hide();
            }
        },
        start: function() {
            var self = this;
            this._super.apply(this, arguments);
            var $oe_systray = this.$el.parents().find('.oe_systray');

            $oe_systray.append(openerp.qweb.render('website.editorbar.edit.not_edit_mode'));
            $oe_systray.show();
            var $topview = $oe_systray.find('#website-top-view');
            
            if (website.MobilePreview) {
                $topview.append(openerp.qweb.render('website.editorbar.menu.mobile_preview'));
                $('a[data-action=show-mobile-preview]', $topview).on('click', this, this.mobilePreview);
            }
            if (website.EditorBarContent) new website.EditorBarContent(this).appendTo($topview);
            if (website.seo) {
                this.$('ul.oe_content_menu').prepend(openerp.qweb.render('website.editorbar.menu.promote'));
                $('a[data-action=promote-current-page]', $topview).on('click', this, this.launchSeo);
            }
            if (website.EditorBarCustomize) new website.EditorBarCustomize(this).appendTo($topview);
            if (website.EditorBarHelp) new website.EditorBarHelp(this).appendTo($topview);

            var lazyreflow = _.debounce(this.reflow.bind(this), 200);
            $(window).on('resize', this, function() {
                if (parseInt(self.$el.parent().css('width')) < 768 ) {
                    lazyreflow('all_outside');
                } else {
                    lazyreflow('all_inside');
                }
            });
        },
    });

    website.ready().done(function () {
        var self = this;
        self.menu = new website.Menu(self);
        self.menu.setElement($('.oe_application_menu_placeholder'));
        self.menu.start();
        if (parseInt(self.menu.$el.parent().css('width')) >= 768 ) {
            self.menu.reflow('all_inside');
        }
    });

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

            this.$('#website-top-edit').hide();
            this.$el.parents().find('#website-top-view').show();

            // $('.dropdown-toggle').dropdown();

            this.$buttons = {
                edit: this.$el.parents().find('button[data-action=edit]'),
                save: this.$('button[data-action=save]'),
                cancel: this.$('button[data-action=cancel]'),
            };

            this.$buttons.edit.click(function(ev) {
                self.edit();
            });

            this.rte = new website.RTE(this);
            this.rte.on('change', this, this.proxy('rte_changed'));
            this.rte.on('rte:ready', this, function () {
                self.setup_hover_buttons();
                self.trigger('rte:ready');
                // self.check_height();
            });

            $(window).on('resize', _.debounce(this.check_height.bind(this), 50));
            this.check_height();

            if (website.is_editable_button) {
                this.$buttons.edit.removeClass("hidden");
            }

            return $.when(
                this._super.apply(this, arguments),
                this.rte.appendTo(this.$('#website-top-edit .nav.js_editor_placeholder'))
            ).then(function () {
                self.check_height();
            });
        },
        check_height: function () {
            // var editor_height = this.$el.outerHeight();
            // if (this.get('height') != editor_height) {
            //     $(document.body).css('padding-top', editor_height);
            //     this.set('height', editor_height);
            // }
        },
        edit: function () {
            this.$buttons.edit.prop('disabled', true);
            this.$('#website-top-view').hide();
            this.$el.show();
            this.$('#website-top-edit').show();
            $('.css_non_editable_mode_hidden').removeClass("css_non_editable_mode_hidden");

            this.rte.start_edition().then(this.check_height.bind(this));
            this.trigger('rte:called');
        },
        rte_changed: function () {
            this.$buttons.save.prop('disabled', false);
        },
        save: function () {
            var self = this;

            website.editor.observer.disconnect();
            var editor = this.rte.editor;
            var root = editor.element && editor.element.$;
            editor.destroy();
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

            // TODO sle: duplicate from website.editor.js
            /**
             * Checks that both the element's content *and the element itself* are
             * editable: an editing host is considered non-editable because its content
             * is editable but its attributes should not be considered editable
             */
            function is_editable_node(element) {
                return !(element.data('oe-model') === 'ir.ui.view'
                      || element.data('cke-realelement')
                      || (element.getAttribute('contentEditable') === 'true' && element.getAttribute('attributeEditable') !== 'true')
                      || element.isReadOnly());
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
})();