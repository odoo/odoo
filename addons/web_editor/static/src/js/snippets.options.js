odoo.define('web_editor.snippets.options', function (require) {
'use strict';

var Class = require('web.Class');
var ajax = require('web.ajax');
var core = require('web.core');
var base = require('web_editor.base');
var editor = require('web_editor.editor');
var widget = require('web_editor.widget');
var animation = require('web_editor.snippets.animation');

var qweb = core.qweb;

/* ----- Editor option (object link the the xml with data-js) ---- */

var Option = Class.extend({
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

/* ----- default options ---- */

// to remove after 9.0 (keep for compatibility without update with -u)
var media = Option.extend({
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

var colorpicker = Option.extend({
    start: function () {
        var self = this;
        var res = this._super();

        var paletteTemplate = '<div class="colorpicker">'+
                       '<div class="note-palette-title">Background Color</div>' +
                       '<div class="btn-group palette-reset">' +
                         '<div class="note-color-reset" data-event="foreColor"' +
                           ' data-value="inherit" title="None"><i class="material-icons">&#xE23B;</i> '+
                         '</div>' +
                       '</div>' +

                       '<div class="tabs_container">' +
                         '<ul class="tabs_toggles">'+
                           '<li class="on"><a href="#" data-tab-target=".palette_theme"><i class="material-icons">&#xE3B7;</i></a></li>' +
                           '<li><a href="#" data-tab-target=".palette_grayscale"><i class="material-icons">&#xE3E9;</i></a></li>' +
                           '<li><a href="#" data-tab-target=".palette_ui"><i class="material-icons">&#xE41D;</i></a></li>' +
                           '<li><a href="#" data-tab-target=".palette_spectrum"><i class="material-icons">&#xE3B8;</i></a></li>' +
                         '</ul>' +
                         '<div class="tabs">' +
                           '<div class="tab palette_theme on"/>'+
                           '<div class="tab palette_grayscale"/>'+
                           '<div class="tab palette_ui"/>'+
                           '<div class="tab palette_spectrum">'+
                             '<div class="note-color-palette"></div>' +
                           '</div>' +
                         '</div>' +
                       '</div>' +

                     '</div></div>';
        var $pt = $(paletteTemplate);

        if (!this.$el.find('.colorpicker').length) {
            var $clpicker = $(qweb.render('web_editor.colorpicker'))
            var pTheme = $clpicker.find('.theme')
            var pGray = $clpicker.find('.grayscale')
            var pUi = $clpicker.find('.ui')
            $pt.find('.palette_theme').append(pTheme).end()
               .find('.palette_grayscale').append(pGray).end()
               .find('.palette_ui').append(pUi)
            this.$el.find('li').append($pt);

            // ACTIVATE TABS
            this.$el.find('[data-tab-target]').each(function(){
              var $el = $(this);
              var target = $el.data('tab-target');
              var $parent = $el.parent().closest('.tabs_container');
              var $parentLi = $el.parent().closest('li');

              $parentLi.on('click', function(){return false});

              $el.on('click', function(){
                $parent.find('.tab, .tabs_toggles li').removeClass('on');
                $parent.find(target).add($parentLi).addClass('on')
                return false;
              })
            })
        }
        if (this.$el.data('area')) {
            this.$target = this.$target.find(this.$el.data('area'));
            this.$el.removeData('area').removeAttr('area');
        }

        var classes = [];
        this.$el.find(".colorpicker button").map(function () {
            var $color = $(this);
            var color = $color.attr("class");
            if (self.$target.hasClass(color)) {
                self.color = color;
                $color.parent().addClass("selected");
            }
            classes.push(color);
        });
        this.classes = classes.join(" ");

        this.bind_events();
        return res;
    },
    bind_events: function () {
        var self = this;
        var $td = this.$el.find(".tab");
        var $colors = this.$el.find(".colorpicker button");
        $colors
            .mouseenter(function () {
                self.$target.removeClass(self.classes).addClass($(this).attr("class"));
            })
            .mouseleave(function () {
                self.$target.removeClass(self.classes)
                    .addClass($colors.filter(".selected").attr("class"));
            })
            .click(function () {
                $colors.removeClass("selected");
                $(this).addClass("selected");
                self.$target.closest(".o_editable").trigger("content_changed");
            });
    }
});

var background_position = Option.extend({
    start: function(){
        var self = this;
        var $btn = self.$overlay.find('.oe_options');
        $btn.on('show.bs.dropdown', function(){
            if (self.$target.css('background-image') == 'none'){
                $btn.find('.background_position_li').addClass('hidden')
            } else {
                $btn.find('.background_position_li').removeClass('hidden')
            }
        })
    },
    background_position: function(type, value, $li){
        if (type != 'click') return;
        var self = this;
        var $modal = $(qweb.render('web_editor.dialog.background_position'));
        $modal.modal()
        $modal.on('hidden.bs.modal', function(){
            setTimeout(function(){
                $modal.remove()
            },2000)
        })
        self.editing(self, $modal)
    },
    editing: function(self, $modal){
        // Init main collapse
        $modal.find(".panel-collapse.collapse").collapse({
            toggle: false,
            parent: $('#bg_image_opt_accordition')
        })

        // Fetch data form $target
        if(self.$target.hasClass('o_bg_img_contain')){
            $modal.find("#bg_size").val('o_bg_img_contain').end()
                  .find("#radio2").prop('checked', true).end()
                  .find("#collapse_contain").collapse('show');

        } else if (self.$target.hasClass('o_bg_img_cover')){
            $modal.find("#bg_size").val('o_bg_img_cover').end()
                  .find("#radio1").prop('checked', true).end()
                  .find("#collapse_cover").collapse('show');
        } else if (self.$target.hasClass('o_bg_img_custom')){
            $modal.find("#bg_size").val('o_bg_img_custom').end()
                  .find("#radio3").prop('checked', true).end()
                  .find("#collapse_custom").collapse('show');
        }
        if(self.$target.hasClass("o_bg_img_repeat")){
            $modal.find("#contain_repeat").prop('checked', true);
            $modal.find("#custom_repeat").val('o_bg_img_repeat')
        } else if (self.$target.hasClass("o_bg_img_no_repeat")){
            $modal.find("#custom_repeat").val('o_bg_img_no_repeat')
        } else if (self.$target.hasClass("o_bg_img_repeat_x")){
            $modal.find("#custom_repeat").val('o_bg_img_repeat_x')
        } else if (self.$target.hasClass("o_bg_img_repeat_y")){
            $modal.find("#custom_repeat").val('o_bg_img_repeat_y')
        }

        var bg_pos = self.$target.css('background-position').split(' '),
            bg_siz = self.$target.css('background-size').split(' ');

        if( bg_pos.length > 1 ) {
            $modal.find("#custom_pos_x").val(bg_pos[0].replace('%',''))
            $modal.find("#custom_pos_y").val(bg_pos[1].replace('%',''))
        }
        if( bg_siz.length > 1 ) {
            $modal.find("#custom_size_x").val(bg_siz[0].replace('%',''))
            $modal.find("#custom_size_y").val(bg_siz[1].replace('%',''))
        }

        // Collapse events
        $('#collapse_cover').on('show.bs.collapse', function(){
            $('#radio1').prop('checked', true);
            $modal.find("#bg_size").val('o_bg_img_cover');
        });

        $('#collapse_contain').on('show.bs.collapse', function(){
            $('#radio2').prop('checked', true);
            $modal.find("#bg_size").val('o_bg_img_contain');
        });

        $('#collapse_custom').on('show.bs.collapse', function(){
            $('#radio3').prop('checked', true);
            $modal.find("#bg_size").val('o_bg_img_custom');
        });

        // Focus Point
        var img_url  = self.$target.css('background-image').replace(/url\(['"]*|['"]*\)|^none$/g, "");

        var $object  = $modal.find(".object"),
            $focus   = $modal.find(".focus_point");

        $modal.find("#pos_x").val(bg_pos[0]).end()
              .find("#pos_y").val(bg_pos[1]).end()
              .find(".ui_info .x").text(bg_pos[0]).end()
              .find(".ui_info .y").text(bg_pos[1])
        $focus.css({
            left: bg_pos[0],
            top:  bg_pos[1]
        })
        setTimeout(function(){$focus.addClass("ready") },50)

        var $img = $('<img class="img-responsive" src="'+ img_url +'"/>')
        $img.prependTo($object)
        $img.on('load',function(){
            self.retrive_click($img, $focus, $modal, self);
        })

        // Save
        $modal.find('.save').on('click',function(){self.save($modal, self) })
    },
    retrive_click: function($img, $focus, $modal, self){
        // Prevent clicks on ui items
        $focus.on('click', function(){$img.mousedown(); })
        $modal.find('.ui_info').on('click', function(){$img.mousedown(); })
        $modal.find('.grid').on('click', function(){$img.mousedown(); })

        // Retrive click position
        $img.click(function (e) {
            var posX  = e.pageX - $(this).offset().left,
                posY  = e.pageY - $(this).offset().top;
            var res = {
                x: (self.range_value(posX/$img.width()*100).toFixed(2)) + '%',
                y: (self.range_value(posY/$img.height()*100).toFixed(2)) + '%'
            };
            $focus.css({top:  res.y, left: res.x })

            $modal.find("#pos_x").val(res.x).end()
                  .find("#pos_y").val(res.y).end()
                  .find(".ui_info .x").text(res.x).end()
                  .find(".ui_info .y").text(res.y).end()
                  .find(".ui_info").hide()

            setTimeout(function(){$modal.find(".ui_info").show() },50)
        });
    },
    range_value: function(value){
        if (value < 0)   value = 0;
        if (value > 100) value = 100;
        return (value)
    },
    save: function($modal, self){
        self.clean(self.$target);
        self.$target.addClass($modal.find("#bg_size").val());
        switch ($modal.find("#bg_size").val()) {
            case "o_bg_img_cover":
                self.$target.css('background-position', $modal.find("#pos_x").val() + ' ' +$modal.find("#pos_y").val())
                break;
            case "o_bg_img_contain":
                if ($modal.find("#contain_repeat").is(":checked")){
                    self.$target.addClass('o_bg_img_repeat')
                } else {
                    self.$target.addClass('o_bg_img_no_repeat')
                }
                break;
            case "o_bg_img_custom":
                self.$target.addClass($modal.find("#custom_repeat").val());
                self.$target.css('background-size',     $modal.find("#custom_size_x").val() + '% ' + $modal.find("#custom_size_y").val() + '%');
                self.$target.css('background-position', $modal.find("#custom_pos_x").val()  + '% ' + $modal.find("#custom_pos_y").val()  + '%');
                break;
        }
    },
    clean: function($target){
        $target.removeClass('o_bg_img_cover o_bg_img_contain o_bg_img_custom o_bg_img_repeat o_bg_img_repeat_x o_bg_img_repeat_y o_bg_img_no_repeat')
               .css('background-size', '')
               .css('background-position', '');
    },
});

var background = Option.extend({
    start: function ($change_target) {
        this.$target = $change_target || this.$target;
        this._super();
        var src = this.$target.css("background-image").replace(/url\(['"]*|['"]*\)|^none$/g, "");
        if (this.$target.hasClass('oe_custom_bg')) {
            this.$el.find('li[data-choose_image]').data("background", src).attr("data-background", src);
        }
    },
    background: function(type, value, $li) {
        if (value && value.length) {
            this.$target.attr("style", 'background-image: url(' + value + '); ' + (this.$target.attr("style") || '').replace(/background-image:[^;]+/, '') );
            this.$target.addClass("oe_img_bg");
        } else {
            this.$target.css("background-image", "");
            this.$target.removeClass("oe_img_bg").removeClass("oe_custom_bg");
        }
    },
    select_class : function(type, value, $li) {
        this.background(type, '', $li);
        this._super(type, value, $li);
    },
    choose_image: function(type, value, $li) {
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

/* t-field options */

var many2one = Option.extend({
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
            .on('keyup', function(e) {
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
        }).then(function (result){
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
                        .then(function (html){
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

/* end*/

return {
    'registry': {
        'media': media,
        'colorpicker': colorpicker,
        'background_position': background_position,
        'background': background,
        'many2one': many2one,
    },
    'Class': Option
};

});
