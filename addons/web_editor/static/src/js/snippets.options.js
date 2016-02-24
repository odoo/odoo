odoo.define('web_editor.snippets.options', function (require) {
    'use strict';

    var Class = require('web.Class');
    var ajax = require('web.ajax');
    var core = require('web.core');
    var Dialog = require('web.Dialog');
    var base = require('web_editor.base');
    var editor = require('web_editor.editor');
    var widget = require('web_editor.widget');
    var animation = require('web_editor.snippets.animation');

    var qweb = core.qweb;
    var _t = core._t;

    /* ----- Editor option (object link the the xml with data-js) ---- */

    var SnippetOption = Class.extend({
        // initialisation (don't overwrite)
        init: function (BuildingBlock, editor, $target, option_id) {
            this.buildingBlock = BuildingBlock;
            this.editor = editor;
            this.$target = $target;
            var option = this.buildingBlock.templateOptions[option_id];
            var styles = this.$target.data("snippet-option-ids") || {};
            styles[option_id] = this;
            this.$target.data("snippet-option-ids", styles);
            this.$overlay = this.$target.data('overlay') || $('<div>');
            this.option= option_id;
            this.$el = option.$el.find(">li").clone();
            this.data = option.$el.data();
        },

        // helper for this.$target.find
        $: function (selector) {
            return this.$target(selector);
        },

        _bind_li_menu: function () {
            this.$el.filter("li:hasData").find('a:first')
                .off('mouseenter click')
                .on('mouseenter click', _.bind(this._mouse, this));

            this.$el
                .off('mouseenter click', "li:hasData a")
                .on('mouseenter click', "li:hasData a", _.bind(this._mouse, this));

            this.$el.closest("ul").add(this.$el)
                .off('mouseleave')
                .on('mouseleave', _.bind(this.reset, this));

            this.$el
                .off('mouseleave', "ul")
                .on('mouseleave', "ul", _.bind(this.reset, this));

            this.reset_methods = [];
        },

        /**
         * this method handles mouse:over and mouse:leave on the snippet editor menu
         */
         _time_mouseleave: null,
        _mouse: function (event) {
            var $next = $(event.currentTarget).parent();

            // triggers preview or apply methods if a menu item has been clicked
            this.select(event.type === "click" ? "click" : "over", $next);
            if (event.type === 'click') {
                this.set_active();
                this.$target.trigger("snippet-option-change", [this]);
            } else {
                this.$target.trigger("snippet-option-preview", [this]);
            }
        },
        /*
        *  select and set item active or not (add highlight item and his parents)
        *  called before start
        */
        set_active: function () {
            var classes = _.uniq((this.$target.attr("class") || '').split(/\s+/));
            this.$el.find('[data-toggle_class], [data-select_class]')
                .add(this.$el)
                .filter('[data-toggle_class], [data-select_class]')
                .removeClass("active")
                .filter('[data-toggle_class="' + classes.join('"], [data-toggle_class="') + '"] ,'+
                    '[data-select_class="' + classes.join('"], [data-select_class="') + '"]')
                .addClass("active");
        },

        start: function () {
            this.set_active();
            this.$target.on('snippet-option-reset', _.bind(this.set_active, this));
            this._bind_li_menu();
        },

        on_focus : function () {
            this._bind_li_menu();
        },

        on_blur : function () {
        },

        on_clone: function ($clone) {
        },

        on_move: function () {
        },

        on_remove: function () {
        },

        drop_and_build_snippet: function () {
        },

        reset: function () {
            var self = this;
            var lis = self.$el.add(self.$el.find('li')).filter('.active').get();
            lis.reverse();
            _.each(lis, function (li) {
                var $li = $(li);
                for (var k in self.reset_methods) {
                    var method = self.reset_methods[k];
                    if ($li.is('[data-'+method+']') || $li.closest('[data-'+method+']').size()) {
                        delete self.reset_methods[k];
                    }
                }
                self.select("reset", $li);
            });

            for (var k in self.reset_methods) {
                var method = self.reset_methods[k];
                if (method) {
                    self[method]("reset", null);
                }
            }
            self.reset_methods = [];
            self.$target.trigger("snippet-option-reset", [this]);
        },

        // call data-method args as method (data-only can be used)
        select: function (type, $li) {
            var self = this,
                $methods = [],
                el = $li[0];

            if ($li.data('only') && type !== $li.data('only')) {
                return;
            }

            if (type==="click") {
                this.reset();
                this.buildingBlock.parent.rte.historyRecordUndo(this.$target);
            }

            function filter (k) { return k !== 'oeId' && k !== 'oeModel' && k !== 'oeField' && k !== 'oeXpath' && k !== 'oeSourceId' && k !== 'only';}
            function hasData(el) {
                for (var k in el.dataset) {
                    if (filter (k)) {
                        return true;
                    }
                }
                return false;
            }
            function method(el) {
                var data = {};
                for (var k in el.dataset) {
                    if (filter (k)) {
                        data[k] = el.dataset[k];
                    }
                }
                return data;
            }

            while (el && this.$el.is(el) || _.some(this.$el.map(function () {return $.contains(this, el);}).get()) ) {
                if (hasData(el)) {
                    $methods.push(el);
                }
                el = el.parentNode;
            }

            $methods.reverse();

            _.each($methods, function (el) {
                var $el = $(el);
                var methods = method(el);

                for (var k in methods) {
                    if (self[k]) {
                        if (type !== "reset" && self.reset_methods.indexOf(k) === -1) {
                            self.reset_methods.push(k);
                        }
                        self[k](type, methods[k], $el);
                    } else {
                        console.error("'"+self.option+"' snippet have not method '"+k+"'");
                    }
                }
            });
        },

        // default method for snippet
        toggle_class: function (type, value, $li) {
            var $lis = this.$el.find('[data-toggle_class]').add(this.$el).filter('[data-toggle_class]');

            function map ($lis) {
                return $lis.map(function () {return $(this).data("toggle_class");}).get().join(" ");
            }
            var classes = map($lis);
            var active_classes = map($lis.filter('.active, :has(.active)'));

            this.$target.removeClass(classes);
            this.$target.addClass(active_classes);

            if (type !== 'reset') {
                this.$target.toggleClass(value);
            }
        },
        select_class: function (type, value, $li) {
            var $lis = this.$el.find('[data-select_class]').add(this.$el).filter('[data-select_class]');

            var classes = $lis.map(function () {return $(this).data('select_class');}).get();

            this.$target.removeClass(classes.join(" "));
            if(value) this.$target.addClass(value);
        },
        eval: function (type, value, $li) {
            var fn = new Function("node", "type", "value", "$li", value);
            fn.call(this, this, type, value, $li);
        },

        clean_for_save: editor.dummy
    });
    var registry = {};

    /* ----- default options ---- */

    // to remove after 9.0 (keep for compatibility without update with -u)
    registry.media = SnippetOption.extend({
        start: function () {
            var self =this;
            this._super();
            animation.start(true, this.$target);
            this.$target.closest(".o_editable").on("content_changed", function () {
                if (!self.$target.parent().length) {
                    self.$target.remove();
                    self.$overlay.remove();
                }
            });
        },
        edition: function (type, value) {
            if(type !== "click") return;
            var self = this;
            var _editor = new widget.MediaDialog(this.$target.closest('.o_editable'), this.$target[0]);
            _editor.appendTo(document.body);
            _editor.on('saved', this, function (item, old) {
                self.editor.on_blur();
                self.buildingBlock.make_active(false);
                if (self.$target.parent().data("oe-field") !== "image") {
                    setTimeout(function () {
                        self.buildingBlock.make_active($(item));
                    },0);
                }
                $(item).trigger("content_changed");
            });
        },
        on_focus : function () {
            var self = this;
            var $parent = this.$target.parent();

            if ($parent.data("oe-field") === "image" && $parent.hasClass('o_editable')) {
                this.$overlay.addClass("hidden");
                self.edition('click', null);
                self.buildingBlock.make_active(false);
            }
        }
    });

    registry.colorpicker = SnippetOption.extend({
        start: function () {
            var self = this;
            var res = this._super();

            if (!this.$el.find('.colorpicker').length) {
                var $pt = $(qweb.render('web_editor.snippet.option.colorpicker'));
                var $clpicker = $(qweb.render('web_editor.colorpicker'));

                var $toggles = $pt.find('.o_colorpicker_section_menu');
                var $tabs = $pt.find('.o_colorpicker_section_tabs');

                var $sections = $clpicker.find('.o_colorpicker_section');
                if ($sections.length) {
                    $sections.each(function () {
                        var $section = $(this);
                        var id = 'o_palette_' + $section.data('name') + _.uniqueId();

                        var $li = $('<li/>')
                                    .append($('<a/>', {href: '#' + id})
                                        .append($('<i/>', {'class': $section.data('iconClass') || '', html: $section.data('iconContent') || ''})));
                        $toggles.append($li);

                        $tabs.append($section.addClass('tab-pane').attr('id', id));
                    });
                    $toggles.find('li').first().addClass('active');
                    $tabs.find('div').first().addClass('active');

                    $toggles.on('click mouseover', '> li > a', function (e) {
                        e.preventDefault();
                        e.stopPropagation();
                        $(this).tab('show');
                    });
                } else {
                    $toggles.parent().empty().append($clpicker);
                }

                this.$el.find('li').append($pt);
            }
            if (this.$el.data('area')) {
                this.$target = this.$target.find(this.$el.data('area'));
                this.$el.removeData('area').removeAttr('area');
            }

            var classes = [];
            this.$el.find(".colorpicker button").map(function () {
                var $color = $(this);
                var className = 'bg-' + $color.data('color');

                $color.addClass(className);

                if (self.$target.hasClass(className)) {
                    self.color = className;
                    $color.addClass("selected");
                }
                classes.push(className);
            });
            this.classes = classes.join(" ");

            this.bind_events();
            return res;
        },
        bind_events: function () {
            var self = this;
            var $colors = this.$el.find(".colorpicker button");
            $colors
                .mouseenter(function () {
                    self.$target.removeClass(self.classes).addClass('bg-' + $(this).data("color"));
                })
                .mouseleave(function () {
                    self.$target.removeClass(self.classes)
                        .addClass('bg-' + $colors.filter(".selected").data("color"));
                })
                .click(function () {
                    $colors.removeClass("selected");
                    $(this).addClass("selected");
                    self.$target.closest(".o_editable").trigger("content_changed");
                });

            this.$el.find('.note-color-reset').on('click', function () {
                self.$target.removeClass(self.classes);
            });
        }
    });

    registry.background = SnippetOption.extend({
        start: function ($change_target) {
            this.$target = $change_target || this.$target;
            this._super();
            var src = this.$target.css("background-image").replace(/url\(['"]*|['"]*\)|^none$/g, "");
            if (this.$target.hasClass('oe_custom_bg')) {
                this.$el.find('li[data-choose_image]').data("background", src).attr("data-background", src);
            }
        },
        background: function (type, value, $li) {
            if (value && value.length) {
                this.$target.attr("style", 'background-image: url(' + value + '); ' + (this.$target.attr("style") || '').replace(/background-image:[^;]+/, '') );
                this.$target.addClass("oe_img_bg");
            } else {
                this.$target.css("background-image", "");
                this.$target.removeClass("oe_img_bg oe_custom_bg");
            }
        },
        select_class : function (type, value, $li) {
            this.background(type, '', $li);
            this._super(type, value, $li);
        },
        choose_image: function (type, value, $li) {
            if(type !== "click") return;

            var self = this;
            var $image = $('<img class="hidden"/>');
            $image.attr("src", value);
            $image.appendTo(self.$target);

            var _editor = new widget.MediaDialog(null, $image[0]);
            _editor.appendTo(document.body);
            _editor.$('[href="#editor-media-video"], [href="#editor-media-icon"]').addClass('hidden');

            _editor.on('saved', self, function () {
                var value = $image.attr("src");
                $image.remove();
                self.$el.find('li[data-choose_image]').data("background", value).attr("data-background", value);
                self.background(type, value,$li);
                self.$target.addClass('oe_custom_bg');
                self.$target.trigger("snippet-option-change", [self]);
                self.set_active();
            });
            _editor.on('cancel', self, function () {
                $image.remove();
            });
        },
        set_active: function () {
            var self = this;
            var src = this.$target.css("background-image").replace(/url\(['"]*|['"]*\)|^none$/g, "");
            this._super();

            if (this.$target.hasClass('oe_custom_bg')) {
                this.$el.find('li[data-choose_image]').data("background", src).attr("data-background", src);
            }

            this.$el.find('li[data-background]:not([data-background=""])')
                .removeClass("active")
                .each(function () {
                    var background = $(this).data("background") || $(this).attr("data-background");
                    if ((src.length && background.length && src.indexOf(background) !== -1) || (!src.length && !background.length)) {
                        $(this).addClass("active");
                    }
                });

            if (!this.$el.find('li[data-background].active').size()) {
                this.$el.find('li[data-background=""]:not([data-choose_image])').addClass("active");
            } else {
                this.$el.find('li[data-background=""]:not([data-choose_image])').removeClass("active");
            }
        }
    });

    registry.background_position = SnippetOption.extend({
        start: function () {
            var self = this;
            var $btn = this.$overlay.find('.oe_options');
            $btn.on('show.bs.dropdown', function () {
                if (self.$target.css('background-image') === 'none') {
                    $btn.find('.background_position_li').addClass('hidden');
                } else {
                    $btn.find('.background_position_li').removeClass('hidden');
                }
            });
        },
        background_position: function (type, value, $li) {
            if (type != 'click') { return; }
            var self = this;

            this.previous_state = [this.$target.attr('class'), this.$target.css('background-size'), this.$target.css('background-position')];

            this.bg_pos = self.$target.css('background-position').split(' ');
            this.bg_siz = self.$target.css('background-size').split(' ');

            this.modal = new Dialog(null, {
                title: _t("Background Image Options"),
                $content: $(qweb.render('web_editor.dialog.background_position')),
                buttons: [
                    {text: _t("Ok"), classes: "btn-primary", close: true, click: _.bind(this.save, this)},
                    {text: _t("Discard"), close: true, click: _.bind(this.discard, this)},
                ],
            }).open();

            this.modal.opened().then(function () {
                // Fetch data form $target
                var value = ((self.$target.hasClass('o_bg_img_opt_contain'))? 'contain' : ((self.$target.hasClass('o_bg_img_opt_custom'))? 'custom' : 'cover'));
                self.modal.$("> label > input[value=" + value + "]").prop('checked', true);

                if(self.$target.hasClass("o_bg_img_opt_repeat")) {
                    self.modal.$("#o_bg_img_opt_contain_repeat").prop('checked', true);
                    self.modal.$("#o_bg_img_opt_custom_repeat").val('o_bg_img_opt_repeat');
                } else if (self.$target.hasClass("o_bg_img_opt_repeat_x")) {
                    self.modal.$("#o_bg_img_opt_custom_repeat").val('o_bg_img_opt_repeat_x');
                } else if (self.$target.hasClass("o_bg_img_opt_repeat_y")) {
                    self.modal.$("#o_bg_img_opt_custom_repeat").val('o_bg_img_opt_repeat_y');
                }

                if(self.bg_pos.length > 1) {
                    self.bg_pos = {
                        x: self.bg_pos[0],
                        y: self.bg_pos[1],
                    };
                    self.modal.$("#o_bg_img_opt_custom_pos_x").val(self.bg_pos.x.replace('%', ''));
                    self.modal.$("#o_bg_img_opt_custom_pos_y").val(self.bg_pos.y.replace('%', ''));
                }
                if(self.bg_siz.length > 1) {
                    self.modal.$("#o_bg_img_opt_custom_size_x").val(self.bg_siz[0].replace('%', ''));
                    self.modal.$("#o_bg_img_opt_custom_size_y").val(self.bg_siz[1].replace('%', ''));
                }

                // Focus Point
                self.$focus  = self.modal.$(".o_focus_point");
                self.update_pos_information();

                var img_url = /\(['"]?([^'"]+)['"]?\)/g.exec(self.$target.css('background-image'));
                img_url = (img_url && img_url[1]) || '';
                var $img = $('<img/>', {'class': 'img img-responsive', src: img_url});
                $img.on('load', function () {
                    self.bind_img_events($img);
                });
                $img.prependTo(self.modal.$(".o_bg_img_opt_object"));

                // Bind events
                self.modal.$el.on('change', '> label > input', function (e) {
                    self.modal.$('> .o_bg_img_opt').addClass('o_hidden')
                                                   .filter("[data-value=" + e.target.value + "]")
                                                   .removeClass('o_hidden');
                });
                self.modal.$el.on('change', 'input, select', function (e) {
                    self.save();
                });
                self.modal.$("> label > input:checked").trigger('change');
            });
        },
        bind_img_events: function ($img) {
            var self = this;

            var mousedown = false;
            $img.on('mousedown', function (e) {
                mousedown = true;
            });
            $img.on('mousemove', function (e) {
                if (mousedown) {
                    _update(e);
                }
            });
            $img.on('mouseup', function (e) {
                self.$focus.addClass('o_with_transition');
                _update(e);
                setTimeout(function () {
                    self.$focus.removeClass('o_with_transition');
                }, 200);
                mousedown = false;
            });

            function _update(e) {
                var posX = e.pageX - $(e.target).offset().left;
                var posY = e.pageY - $(e.target).offset().top;
                self.bg_pos = {
                    x: clip_value(posX/$img.width()*100).toFixed(2) + '%',
                    y: clip_value(posY/$img.height()*100).toFixed(2) + '%',
                };
                self.update_pos_information();
                self.save();
            }

            function clip_value(value) {
                return Math.max(0, Math.min(value, 100));
            }
        },
        update_pos_information: function () {
            this.modal.$(".o_bg_img_opt_ui_info .o_x").text(this.bg_pos.x);
            this.modal.$(".o_bg_img_opt_ui_info .o_y").text(this.bg_pos.y);
            this.$focus.css({
                left: this.bg_pos.x,
                top: this.bg_pos.y,
            });
        },
        save: function () {
            this.clean();

            var bg_img_size = this.modal.$('> :not(label):not(.o_hidden)').data('value') || 'cover';
            switch (bg_img_size) {
                case "cover":
                    this.$target.css('background-position', this.bg_pos.x + ' ' + this.bg_pos.y);
                    break;
                case "contain":
                    this.$target.addClass('o_bg_img_opt_contain');
                    this.$target.toggleClass('o_bg_img_opt_repeat', this.modal.$("#o_bg_img_opt_contain_repeat").prop("checked"));
                    break;
                case "custom":
                    this.$target.addClass('o_bg_img_opt_custom');
                    var sizeX = this.modal.$("#o_bg_img_opt_custom_size_x").val();
                    var sizeY = this.modal.$("#o_bg_img_opt_custom_size_y").val();
                    var posX = this.modal.$("#o_bg_img_opt_custom_pos_x").val();
                    var posY = this.modal.$("#o_bg_img_opt_custom_pos_y").val();
                    this.$target.addClass(this.modal.$("#o_bg_img_opt_custom_repeat").val())
                                .css({
                                    'background-size': ((sizeX)? sizeX + '%' : 'auto') + " " + ((sizeY)? sizeY + '%' : 'auto'),
                                    'background-position': ((posX)? posX + '%' : 'auto') + " " + ((posY)? posY + '%' : 'auto'),
                                });
                    break;
            }
        },
        discard: function () {
            this.clean();
            if (this.previous_state) {
                this.$target.addClass(this.previous_state[0]).css({
                    'background-size': this.previous_state[1],
                    'background-position': this.previous_state[2],
                });
            }
        },
        clean: function () {
            this.$target.removeClass('o_bg_img_opt_contain o_bg_img_opt_custom o_bg_img_opt_repeat o_bg_img_opt_repeat_x o_bg_img_opt_repeat_y')
                        .css({
                            'background-size': '',
                            'background-position': '',
                        });
        },
    });

    /* t-field options */

    registry.many2one = SnippetOption.extend({
        start: function () {
            var self = this;

            this.Model = this.$target.data('oe-many2one-model');
            this.ID = +this.$target.data('oe-many2one-id');

            // create search button and bind search bar
            this.$btn = $(qweb.render("web_editor.many2one.button"))
                .insertAfter(this.$overlay.find('.oe_options'));

            this.$ul = this.$btn.find("ul");
            this.$search = this.$ul.find('li:first');
            this.$search.find('input').on('mousedown click mouseup keyup keydown', function (e) {
                e.stopPropagation();
            });

            // move menu item
            setTimeout(function () {
                if (self.$overlay.find('.oe_options').hasClass('hidden')) {
                    self.$btn.css('height', '0').find('> a').addClass('hidden');
                    self.$ul.show().css({
                        'top': '-24px', 'margin': '0', 'padding': '2px 0', 'position': 'relative'
                    });
                } else {
                    self.$btn.find('a').on('click', function (e) {
                        self.clear();
                    });
                }
            },0);

            // bind search input
            this.$search.find('input')
                .focus()
                .on('keyup', function (e) {
                    self.find_existing($(this).val());
                });

            // bind result
            this.$ul.on('click', "li:not(:first) a", function (e) {
                self.select_record(this);
            });
        },

        on_focus: function () {
            this.$target.attr('contentEditable', 'false');
            this.clear();
            this._super();
        },

        clear: function () {
            var self = this;
            this.$search.siblings().remove();
            self.$search.find('input').val("");
            setTimeout(function () {
                self.$search.find('input').focus();
            },0);
        },

        find_existing: function (name) {
            var self = this;
            var domain = [];
            if (!name || !name.length) {
                self.$search.siblings().remove();
                return;
            }
            if (isNaN(+name)) {
                if (this.Model !== "res.partner") {
                    domain.push(['name', 'ilike', name]);
                } else {
                    domain.push('|', ['name', 'ilike', name], ['email', 'ilike', name]);
                }
            } else {
                domain.push(['id', '=', name]);
            }

            ajax.jsonRpc('/web/dataset/call_kw', 'call', {
                model: this.Model,
                method: 'search_read',
                args: [domain, this.Model === "res.partner" ? ['name', 'display_name', 'city', 'country_id'] : ['name', 'display_name']],
                kwargs: {
                    order: 'name DESC',
                    limit: 5,
                    context: base.get_context(),
                }
            }).then(function (result) {
                self.$search.siblings().remove();
                self.$search.after(qweb.render("web_editor.many2one.search",{contacts:result}));
            });
        },

        get_contact_rendering: function (options) {
            return ajax.jsonRpc('/web/dataset/call_kw', 'call', {
                model: 'ir.qweb.field.contact',
                method: 'get_record_to_html',
                args: [[this.ID]],
                kwargs: {
                    options: options,
                    context: base.get_context(),
                }
            });
        },

        select_record: function (li) {
            var self = this;

            this.ID = +$(li).data("id");
            this.$target.attr('data-oe-many2one-id', this.ID).data('oe-many2one-id', this.ID);

            this.buildingBlock.parent.rte.historyRecordUndo(this.$target);
            this.$target.trigger('content_changed');

            if (self.$target.data('oe-type') === "contact") {
                $('[data-oe-contact-options]')
                    .filter('[data-oe-model="'+self.$target.data('oe-model')+'"]')
                    .filter('[data-oe-id="'+self.$target.data('oe-id')+'"]')
                    .filter('[data-oe-field="'+self.$target.data('oe-field')+'"]')
                    .filter('[data-oe-contact-options!="'+self.$target.data('oe-contact-options')+'"]')
                    .add(self.$target)
                    .attr('data-oe-many2one-id', self.ID).data('oe-many2one-id', self.ID)
                    .each(function () {
                        var $node = $(this);
                        self.get_contact_rendering($node.data('oe-contact-options'))
                            .then(function (html) {
                                $node.html(html);
                            });
                    });
            } else {
                self.$target.html($(li).data("name"));
            }

            setTimeout(function () {
                self.buildingBlock.make_active(false);
            },0);
        }
    });

    return {
        registry: registry,
        Class: SnippetOption,
    };
});
