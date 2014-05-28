(function () {
    'use strict';
    
    var website = openerp.website;
    var _t = openerp._t;

    website.Menu =  openerp.Widget.extend({
        start: function() {
            var self = this;
            this._super.apply(this, arguments);

            if (website.EditorBarCustomize) new website.EditorBarCustomize(this).appendTo(this.$el);
            if (website.EditorBarHelp) new website.EditorBarHelp(this).appendTo(this.$el);
        },
    });

    website.ready().done(function () {
        var self = this;
        self.menu = new website.Menu(self);
        self.menu.setElement($('.nav.navbar-nav.navbar-left'));
        self.menu.start();
    });

    /* ----- TOP EDITOR BAR FOR ADMIN ---- */
    website.EditorBar = openerp.Widget.extend({
        template: 'website.editorbar',
        events: {
            'click button[data-action=edit]': 'edit',
            'click button[data-action=save]': 'save',
            'click a[data-action=cancel]': 'cancel',
            'click a[data-action=show-mobile-preview]': 'mobilePreview',
            'click a[data-action=promote-current-page]': 'launchSeo',
        },
        container: 'body',
        start: function() {
            // remove placeholder editor bar
            var fakebar = document.getElementById('website-top-navbar-placeholder');
            if (fakebar) {
                fakebar.parentNode.removeChild(fakebar);
            }

            var self = this;
            this.saving_mutex = new openerp.Mutex();

            this.$('#website-top-edit').hide();
            this.$('#website-top-view').show();

            $('.dropdown-toggle').dropdown();

            // display menu

            this.$menu = this.$("#website-top-view-menu");
            if (website.MobilePreview) this.$menu.append(openerp.qweb.render('website.editorbar.menu.mobile_preview'));
            if (website.seo) this.$menu.append(openerp.qweb.render('website.editorbar.menu.promote'));
            if (website.EditorBarContent) new website.EditorBarContent(this).appendTo(this.$menu);

            // end

            this.$buttons = {
                edit: this.$('button[data-action=edit]'),
                save: this.$('button[data-action=save]'),
                cancel: this.$('button[data-action=cancel]'),
            };

            this.rte = new website.RTE(this);
            this.rte.on('change', this, this.proxy('rte_changed'));
            this.rte.on('rte:ready', this, function () {
                self.setup_hover_buttons();
                self.trigger('rte:ready');
                self.check_height();
            });

            $(window).on('resize', _.debounce(this.check_height.bind(this), 50));
            this.check_height();

            if (website.is_editable_button) {
                this.$("button[data-action=edit]").removeClass("hidden");
            }

            return $.when(
                this._super.apply(this, arguments),
                this.rte.appendTo(this.$('#website-top-edit .nav.pull-right'))
            ).then(function () {
                self.check_height();
            });
        },
        mobilePreview: function () {
            (new website.MobilePreview()).appendTo($(document.body));
        },
        launchSeo: function () {
            (new website.seo.Configurator(this)).appendTo($(document.body));
        },
        check_height: function () {
            var editor_height = this.$el.outerHeight();
            if (this.get('height') != editor_height) {
                $(document.body).css('padding-top', editor_height);
                this.set('height', editor_height);
            }
        },
        edit: function () {
            this.$buttons.edit.prop('disabled', true);
            this.$('#website-top-view').hide();
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

            observer.disconnect();
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