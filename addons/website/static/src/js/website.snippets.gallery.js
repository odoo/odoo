odoo.define('website.snippets.editor.gallery', function (require) {
'use strict';

var ajax = require('web.ajax');
var core = require('web.core');
var base = require('web_editor.base');
var widget = require('web_editor.widget');
var animation = require('web_editor.snippets.animation');
var options = require('web_editor.snippets.options');
var snippet_editor = require('web_editor.snippet.editor');

var _t = core._t;
var qweb = core.qweb;

/*--------------------------------------------------------------------------
 Template files to load
 --------------------------------------------------------------------------*/
ajax.loadXML('/website/static/src/xml/website.gallery.xml', qweb);

/*--------------------------------------------------------------------------
  Gallery Snippet

  This is the snippet responsible for configuring the image galleries.
  Look at /website/views/snippets.xml for the available options
  ------------------------------------------------------------------------*/
options.registry.gallery = options.Class.extend({
    start  : function () {
        this._super();
        this.bind_change();
        var index = Math.max(_.map(this.$target.find("img").get(), function (img) { return img.dataset.index | 0; }));
        this.$target.find("img:not([data-index])").each(function () {
            index++;
            $(this).attr('data-index', index).data('index', index);
        });
        this.$target.attr("contentEditable", false);

        this._temp_mode = this.$el.find("data-mode").data("mode");
        this._temp_col = this.$el.find("data-columns").data("columns");
    },
    drop_and_build_snippet: function () {
        var uuid = new Date().getTime();
        this.$target.find('.carousel').attr('id', 'slideshow_' + uuid);
        this.$target.find('[data-target]').attr('data-target', '#slideshow_' + uuid);
    },
    styling  : function (type, value) {
        var classes = this.$el.find('li[data-styling]').map(function () {
            return $(this).data('styling');
        }).get().join(' ');
        this.$target.find("img").removeClass(classes).addClass(value);
    },
    interval : function (type, value) {
        this.$target.find('.carousel:first').attr("data-interval", value);
    },
    reapply : function () {
        var self    = this,
            modes   = [ 'o_nomode', 'o_grid', 'o_masonry', 'o_slideshow' ],
            classes = this.$target.attr("class").split(/\s+/);
        this.cancel_masonry();

        modes.forEach(function (mode) {
            if (classes.indexOf(mode) != -1) {
                self.mode("reapply", mode.slice(2, Infinity));
                return;
            }
        });
        this.$target.attr("contentEditable", false);
    },
    bind_change: function () {
        var self = this;
        return this.$target.find("img").off('save').on('save', function (event, img) {
                var $parent = $(img).parent();
                $parent.addClass("saved_active");
                var index = self.$target.find(".item.saved_active").index();
                $parent.removeClass("saved_active");
                self.$target.find(".carousel:first li[data-target]:eq("+index+")").css("background-image", "url("+$(img).attr("src")+")");
            });
    },
    get_imgs: function () {
        var imgs = this.$target.find("img").addClass("img img-thumbnail img-responsive mb8 mt8").detach().get();
        imgs.sort(function (a,b) { return $(a).data('index')-$(b).data('index'); });
        return imgs;
    },
    mode: function (type, value, $li) {
        if (type !== "reapply" && type !== "click" && this._temp_mode === value) {
            return;
        }
        this._temp_mode = value;

        this.cancel_masonry();

        if (!value) value = 'nomode';
        this[value](type);
        this.$target.removeClass('o_nomode o_masonry o_grid o_slideshow').addClass("o_"+value);
        this.bind_change();
    },
    replace: function ($content) {
        var $container = this.$target.find(".container:first");
        $container.empty().append($content);
        return $container;
    },
    nomode : function (type) {
        if (type !== "reapply" && !this.$target.attr('class').match(/o_grid|o_masonry|o_slideshow/)) return;

        var self = this,
            $row     = $('<div class="row"></div>'),
            $imgs = $(this.get_imgs());

        this.replace($row);

        $imgs.each(function () {
            var $wrap = $(this).wrap('<div>').parent();
            var img = this;
            if (img.width >= img.height * 2) {
                $wrap.addClass("col-md-6");
            } else if (img.width > 600) {
                $wrap.addClass("col-md-6");
            } else {
                $wrap.addClass("col-md-3");
            }
            $row.append($wrap);
        });
        this.$target.css("height", "");
    },
    cancel_masonry: function () {
        clearTimeout(this.timer);
        $(this.masonry_imgs).appendTo(this.$target);
        this.masonry_imgs = [];
    },
    masonry : function (type) {
        var self     = this,
            imgs    = this.get_imgs(),
            columns  = this.get_columns(),
            colClass = undefined,
            $cols    = [];

        var $row = $("<div class='row'/>");
        this.replace($row);

        // if no columns let's default to 3, here we must update the DOM accordingly :'(
        if (columns === 0) {
            columns = 3;
            this.$target.attr("data-columns", columns);
        }
        colClass = "col-md-"+(12/columns);

        // create columns
        for (var c = 0; c < columns; c++) {
            var $col = $('<div class="col o_snippet_not_selectable"></div>').addClass(colClass);
            $row.append($col);
            $cols.push($col.get()[0]);
        }

        imgs.reverse();
        $cols = $($cols);
        function add() {
            self.lowest($cols).append(imgs.pop());
            if (imgs.length) self.timer = setTimeout(add, 0);
        }
        this.masonry_imgs = imgs;
        if (imgs.length) add();
        this.$target.css("height", "");
    },
    grid : function (type) {
        if (type !== "reapply" && this.$target.hasClass('o_grid')) return;

        var self     = this,
            $imgs    = $(this.get_imgs()),
            $col, $img,
            $row     = $('<div class="row"></div>'),
            columns  = this.get_columns() || 3,
            colClass = "col-md-"+(12/columns),
            $container = this.replace($row);

        $imgs.each(function (index) { // 0 based index
            $img = $(this);
            $col = $img.wrap('<div>').parent();
            self.img_preserve_styles($img);
            self.img_responsive($img);
            $col.addClass(colClass);
            $col.appendTo($row);
            if ( (index+1) % columns === 0) {
                $row = $('<div class="row"></div>');
                $row.appendTo($container);
            }
        });
        this.$target.css("height", "");
    },
    slideshow :function (type) {
        if (type !== "reapply" && this.$target.hasClass('o_slideshow')) return;

        var self = this,
            $imgs    = $(this.get_imgs()),
            urls = $imgs.map(function () { return $(this).attr("src"); } ).get();
        var params = {
                srcs : urls,
                index: 0,
                title: "",
                interval : this.$target.data("interval") || false,
                id: "slideshow_" + new Date().getTime()
            },
            $slideshow = $(qweb.render('website.gallery.slideshow', params));
        this.replace($slideshow);
        this.$target.find(".item img").each(function (index) {
            $(this).attr('data-index', index).data('index', index);
        });
        this.$target.css("height", Math.round(window.innerHeight*0.7));

        // apply layout animation
        this.$target.off('slide.bs.carousel').off('slid.bs.carousel');
        this.$target.find('li.fa').off('click');
        if (this.$target.data("snippet-view", view)) {
            var view = new animation.registry.gallery_slider(this.$target, true);
            this.$target.data("snippet-view", view);
        } else {
            this.$target.data("snippet-view").start(true);
        }
    },
    columns : function (type, value) {
        this.$target.attr("data-columns", value);
        if (this._temp_col !== value) {
            this._temp_col = value;
            this.reapply();
        }
    },
    images_add : function (type) {
        if(type !== "click") return;
        var self = this;
        var $container = this.$target.find(".container:first");
        var editor = new widget.MediaDialog(null, {select_images: true}, this.$target.closest('.o_editable'), null).open();
        var index = Math.max(0, _.max(_.map(this.$target.find("img").get(), function (img) { return img.dataset.index | 0; })) + 1);
        editor.on('save', this, function (attachments) {
            for (var i = 0 ; i < attachments.length; i++) {
                $('<img class="img img-responsive mb8 mt8"/>')
                    .attr("src", attachments[i].src)
                    .attr('data-index', index+i)
                    .data('index', index+i)
                    .appendTo($container);
            }
            self.reapply(); // refresh the $target
            setTimeout(function () {
                self.buildingBlock.make_active(self.$target);
            },0);
        });
    },
    images_rm   : function (type) {
        if(type !== "click") return;
        this.replace($('<div class="alert alert-info css_editable_mode_display"/>').text(_t("Add Images from the 'Customize' menu")));
    },
    sizing : function () { // done via css, keep it to avoid undefined error
    },
    /*
     *  helpers
     */
    styles_to_preserve : function ($img) {
        var styles = [ 'img-rounded', 'img-thumbnail', 'img-circle', 'shadow', 'fa-spin' ];
        var preserved = [];

        for (var style in styles) {
            if ($img.hasClass(style)) {
                preserved.push(style);
            }
        }
        return preserved.join(' ');
    },
    img_preserve_styles : function ($img) {
        var classes = this.styles_to_preserve($img);
        $img.removeAttr("class");
        $img.addClass(classes);
        return $img;
    },
    img_responsive : function (img) {
        img.addClass("img img-responsive");
        return img;
    },
    lowest : function ($cols) {
        var height = 0, min = -1, col=0, lowest = undefined;
        $cols.each(function () {
            var $col = $(this);
            height = $col.height();
            if (min === -1 || height < min) {
                min = height;
                lowest = $col;
            }
        });
        return lowest;
    },
    get_columns : function () {
        return parseInt(this.$target.attr("data-columns") || 3);
    },

    clean_for_save: function () {
        var self = this;
        if (this.$target.hasClass("slideshow")) {
            this.$target.removeAttr("style");
        }
    },

    set_active: function () {
        this._super();
        var classes = _.uniq((this.$target.attr("class").replace(/(^|\s)o_/g, ' ') || '').split(/\s+/));
        var $li = this.$el.find('[data-mode]')
            .removeClass("active")
            .filter('[data-mode="' + classes.join('"], [data-mode="') + '"]').addClass("active");
        var mode = this.$el.find('[data-mode].active').data('mode');

        var classes = _.uniq((this.$target.find("img:first").attr("class") || '').split(/\s+/));
        var $li = this.$el.find('[data-styling]')
            .removeClass("active")
            .filter('[data-styling="' + classes.join('"], [data-styling="') + '"]').addClass("active");

        this.$el.find('li[data-interval]').removeClass("active")
            .filter('li[data-interval='+this.$target.find(".carousel:first").attr("data-interval")+']')
            .addClass("active");

        var interval = this.$target.find('.carousel:first').attr("data-interval");
        var $li = this.$el.find('[data-interval]')
            .removeClass("active")
            .filter('[data-interval=' + interval + ']').addClass("active");

        var columns = this.get_columns();
        var $li = this.$el.find('[data-columns]')
            .removeClass("active")
            .filter('[data-columns=' + columns + ']').addClass("active");

        this.$el.find('[data-columns]:first, [data-select_class="spc-none"]')
            .parent().parent().toggle(["grid", "masonry"].indexOf(mode) !== -1);
        this.$el.find('[data-interval]:first').parent().parent().toggle(mode === "slideshow");
    },
}); // options.Class.extend


options.registry.gallery_img = options.Class.extend({
    position: function (type, value) {
        if (type !== "click") return;

        var $parent = this.$target.closest("section");
        var editor = $parent.data('snippet-editor').styles.gallery;
        var imgs = $parent.find('img').get();
        imgs.sort(function (a,b) { return $(a).data('index')-$(b).data('index'); });

        var index = imgs.indexOf(this.$target[0]);

        switch (value) {
            case 'first': index = $(imgs.shift()).data('index')-1; break;
            case 'prev': index = index <= 1  ? $(imgs.shift()).data('index')-1 : ($(imgs[index-2]).data('index') + $(imgs[index-1]).data('index'))/2; break;
            case 'next': index = index >= imgs.length-2  ? $(imgs.pop()).data('index')+1 : ($(imgs[index+2]).data('index') + $(imgs[index+1]).data('index'))/2; break;
            case 'last': index = $(imgs.pop()).data('index')+1; break;
        }

        this.$target.data('index',index);

        this.buildingBlock.make_active(false);
        setTimeout(function () {
            editor.reapply();
        },0);
    },
    on_remove: function () {
        var $parent = snippet_editor.globalSelector.closest(this.$target.parent());
        _.defer((function () {
            this.buildingBlock.make_active($parent);
            $parent.data('snippet-editor').styles.gallery.reapply();
        }).bind(this));
    },
    on_focus: function () {
        this._super.apply(this, arguments);
        if (this._current_src && this._current_src !== this.$target.attr("src")) {
            _.defer((function () {
                snippet_editor.globalSelector.closest(this.$target.parent()).data('snippet-editor').styles.gallery.reapply();
            }).bind(this));
        }
        this._current_src = this.$target.attr("src");
    },
});


});
