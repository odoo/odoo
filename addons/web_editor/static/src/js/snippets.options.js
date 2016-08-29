odoo.define('web_editor.snippets.options', function (require) {
    'use strict';

    var ajax = require('web.ajax');
    var Class = require('web.Class');
    var core = require('web.core');
    var Dialog = require('web.Dialog');
    var base = require('web_editor.base');
    var editor = require('web_editor.editor');
    var widget = require('web_editor.widget');

    var qweb = core.qweb;
    var _t = core._t;

    /**
     * The SnippetOption class handles one option for one snippet. The registry returned by
     * this module contains the names of the specialized SnippetOption which can be reference
     * thanks to the data-js key of the full options web_editor template.
     */
    var SnippetOption = Class.extend({
        init: function (BuildingBlock, editor, $target, option_id) {
            this.buildingBlock = BuildingBlock;
            this.editor = editor;
            this.$target = $target;

            this.option = option_id;
            var option = this.buildingBlock.templateOptions[option_id];
            this.$el = option.$el.children("li").clone();
            this.data = option.$el.data();

            this.$overlay = this.$target.data('overlay') || $();
        },

        // helper for this.$target.find
        $: function () {
            return this.$target.find.apply(this.$target, arguments);
        },

        _bind_li_menu: function () {
            this.$el.filter("li:hasData").find('a:first')
                .off('mouseenter click')
                .on('mouseenter click', _.bind(_mouse, this));

            this.$el
                .off('mouseenter click', "li:hasData a")
                .on('mouseenter click', "li:hasData a", _.bind(_mouse, this));

            this.$el.off('mouseleave')
                    .on('mouseleave', _.bind(this.reset, this));

            this.$el.off('mouseleave', "ul")
                    .on('mouseleave', "ul", _.bind(this.reset, this));

            this.methodsToReset = [];

            function _mouse(event) {
                var $next = $(event.currentTarget).parent();

                // triggers preview or apply methods if a menu item has been clicked
                this.select(event.type === "click" ? "click" : "over", $next);
                if (event.type === 'click') {
                    this.set_active();
                    this.$target.trigger("snippet-option-change", [this]);
                } else {
                    this.$target.trigger("snippet-option-preview", [this]);
                }
            }
        },

        /**
         * The set_active method tweaks the option dropdown to show the selected value
         * according to the state of the $target the option customizes.
         */
        set_active: function () {
            var self = this;
            this.$el.find('[data-toggle_class], [data-select_class]')
                .addBack('[data-toggle_class], [data-select_class]')
                .removeClass("active")
                .filter(function () {
                    var $elem = $(this);
                    var className = $elem.data("toggle_class") || $elem.data("select_class");
                    return self.$target.hasClass(className);
                })
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

        on_blur : function () {},
        on_clone: function ($clone) {},
        on_move: function () {},
        on_remove: function () {},

        drop_and_build_snippet: function () {},

        reset: function () {
            var self = this;
            var lis = this.$el.find("li.active").addBack('.active').get();
            _.each(lis.reverse(), function (li) {
                var $li = $(li);
                for (var k in self.methodsToReset) {
                    var method = self.methodsToReset[k];
                    if ($li.closest('[data-' + method + ']').length) {
                        delete self.methodsToReset[k];
                    }
                }
                self.select("reset", $li);
            });

            for (var k in this.methodsToReset) {
                var method = this.methodsToReset[k];
                if (method) {
                    this[method]("reset", null);
                }
            }
            this.methodsToReset = [];
            this.$target.trigger("snippet-option-reset", [this]);
        },

        /**
         * Handle action type on a particuler $li (sub)option of the option.
         * @param type action type to handle ("click", "over", "reset")
         * @param $li the suboption DOM element which is concerned by the action
         */
        select: function (type, $li) {
            // (sub)options can say they respond to only one action type
            if ($li.data('only') && type !== $li.data('only')) {
                return;
            }
            // If the type is click, the user selected the option for good (so reset and record action)
            if (type === "click") {
                this.reset();
                this.buildingBlock.getParent().rte.historyRecordUndo(this.$target);
            }

            // Search for methods (data-...) (i.e. data-toggle_class) on the selected (sub)option and its parents
            var el = $li[0];
            var methods = [];
            do {
                var m = _.omit(el.dataset, ["oeId", "oeModel", "oeField", "oeXpath", "oeSourceId", "only"]);
                if (_.keys(m).length) {
                    methods.push([el, m]);
                }
                el = el.parentNode;
            } while (this.$el.parent().has(el).length);

            // Call the found method in the right order (parents -> child) and save them for later reset
            var self = this;
            _.each(methods.reverse(), function (data) {
                var $el = $(data[0]);
                var methods = data[1];

                for (var k in methods) {
                    if (self[k]) {
                        if (type !== "reset" && self.methodsToReset.indexOf(k) === -1) {
                            self.methodsToReset.push(k);
                        }
                        self[k](type, methods[k], $el);
                    } else {
                        console.error("'" + self.option + "' snippet option have not method '" + k + "'");
                    }
                }
            });
        },

        /**
         * Default option methods toggle_class and selected_class handle the two behavior of having a list
         * of option classes to toggle or not and having a list of option classes where only one must be chosen.
         */
        toggle_class: function (type, value, $li) {
            var $lis = this.$el.find("[data-toggle_class]").addBack("[data-toggle_class]");

            function map($lis) {
                return $lis.map(function () {return $(this).data("toggle_class");}).get().join(" ");
            }
            var classes = map($lis);
            var active_classes = map($lis.filter('.active, :has(.active)'));

            this.$target.removeClass(classes).addClass(active_classes);
            if (type !== 'reset') {
                this.$target.toggleClass(value);
            }
        },
        select_class: function (type, value, $li) {
            var $lis = this.$el.find("[data-select_class]").addBack("[data-select_class]");

            var classes = $lis.map(function () {return $(this).data("select_class");}).get().join(" ");

            this.$target.removeClass(classes);
            if (value) {
                this.$target.addClass(value);
            }
        },

        /**
         * Helper method to evaluate the value expression directly as a function
         */
        eval: function (type, value, $li) {
            var fn = new Function("node", "type", "value", "$li", value);
            fn.call(this, this, type, value, $li);
        },

        clean_for_save: editor.dummy
    });
    var registry = {};

    /* ----- default options ---- */

    /**
     * The colorpicker option is designed to change the background color class of a snippet. This class change the
     * default background color and text color of the snippet content.
     */
    registry.colorpicker = SnippetOption.extend({
        start: function () {
            var self = this;
            var res = this._super.apply(this, arguments);

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
                .mouseenter(function (e) {
                    self.$target.removeClass(self.classes).addClass('bg-' + $(this).data("color"));
                    self.$target.trigger("background-color-event", e.type);
                })
                .mouseleave(function (e) {
                    self.$target.removeClass(self.classes);
                    var $selected = $colors.filter(".selected");
                    if ($selected.length) {
                        self.$target.addClass('bg-' + $selected.data("color"));
                    }
                    self.$target.trigger("background-color-event", e.type);
                })
                .click(function (e) {
                    $colors.removeClass("selected");
                    $(this).addClass("selected");
                    self.$target.closest(".o_editable").trigger("content_changed");
                    self.$target.trigger("background-color-event", e.type);
                });

            this.$el.find('.note-color-reset').on('click', function () {
                self.$target.removeClass(self.classes);
                $colors.removeClass("selected");
            });
        }
    });

    /**
     * The background option is designed to change the background image of a snippet.
     */
    registry.background = SnippetOption.extend({
        start: function () {
            var res = this._super.apply(this, arguments);
            this.$target.off(".background-option")
                        .on("background-color-event.background-option", (function (e, type) {
                            this.$el.find("li:first > a").trigger(type);
                        }).bind(this));
            return res;
        },

        background: function (type, value, $li) {
            if (value && value.length) {
                this.$target.css("background-image", "url(" + value + ")");
                this.$target.addClass("oe_img_bg");
            } else {
                this.$target.css("background-image", "");
                this.$target.removeClass("oe_img_bg oe_custom_bg");
            }
        },
        select_class: function (type, value, $li) {
            this.background(type, '', $li);
            this._super(type, value ? (value + " oe_img_bg") : value, $li);
        },
        choose_image: function (type, value, $li) {
            if(type !== "click") {
                return;
            }

            // Put fake image in the DOM, edit it and use it as background-image
            var $image = $("<img/>", {"class": "hidden", "src": value}).appendTo(this.$target);

            var _editor = new widget.MediaDialog(null, {}, null, $image[0]).open();
            _editor.$('[href="#editor-media-video"], [href="#editor-media-icon"]').addClass('hidden');

            _editor.on('saved', this, function () {
                var value = $image.attr("src");
                this.background(type, value, $li);
                this.$target.addClass("oe_custom_bg");
                this.set_active();
                this.$target.trigger("snippet-option-change", [this]);
            });
            _editor.on('closed', this, function () {
                $image.remove();
            });
        },
        set_active: function () {
            this._super.apply(this, arguments);

            var src = this.$target.css("background-image").replace(/url\(['"]*|['"]*\)|^none$/g, "");
            if (this.$target.hasClass('oe_custom_bg')) {
                this.$el.find('li[data-choose_image]').data("background", src).attr("data-background", src);
            }

            this.$el.find('li[data-background]')
                .removeClass("active")
                .filter(function () {
                    var bgOption = $(this).data("background");
                    return (bgOption === "" && src === "" || bgOption !== "" && src.indexOf(bgOption) >= 0);
                })
                .addClass("active");
        }
    });

    /**
     * The background_position option is designed to change the background image position of a snippet.
     */
    registry.background_position = SnippetOption.extend({
        start: function () {
            this._super.apply(this, arguments);
            this.on_focus();
            var self = this;
            this.$target.on("snippet-option-change", function () {
                self.on_focus();
            });
        },
        on_focus: function () {
            this._super.apply(this, arguments);
            this.$el.toggleClass('hidden', this.$target.css('background-image') === 'none');
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
            this._super.apply(this, arguments);
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

            this.buildingBlock.getParent().rte.historyRecordUndo(this.$target);
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
        Class: SnippetOption,
        registry: registry,
    };
});
