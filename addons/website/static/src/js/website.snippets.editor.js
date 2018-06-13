odoo.define('website.snippets.editor', function (require) {
'use strict';

var ajax = require("web.ajax");
var core = require("web.core");
var Dialog = require("web.Dialog");
var Model = require("web.Model");
var editor = require("web_editor.editor");
var animation = require('web_editor.snippets.animation');
var options = require('web_editor.snippets.options');
var snippet_editor = require('web_editor.snippet.editor');
var website = require('website.website');

var _t = core._t;

snippet_editor.Class.include({
    _get_snippet_url: function () {
        return '/website/snippets';
    }
});

options.registry.menu_data = options.Class.extend({
    start: function () {
        this._super.apply(this, arguments);
        this.link = this.$target.attr("href");
    },

    on_focus: function () {
        this._super.apply(this, arguments);

        (new Dialog(null, {
            title: _t("Confirmation"),
            $content: $(core.qweb.render("website.leaving_current_page_edition")),
            buttons: [
                {text: _t("Go to Link"), classes: "btn-primary", click: save_editor_then_go_to.bind(null, this.link)},
                {text: _t("Edit the menu"), classes: "btn-primary", click: function () {
                    var self = this;
                    website.topBar.content_menu.edit_menu(function () {
                        return editor.editor_bar.save_without_reload();
                    }).then(function (dialog) {
                        self.close();
                    });
                }},
                {text: _t("Stay on this page"), close: true}
            ]
        })).open();

        function save_editor_then_go_to(url) {
            editor.editor_bar.save_without_reload().then(function () {
                window.location.href = url;
            });
        }
    },
});

options.registry.company_data = options.Class.extend({
    start: function () {
        this._super.apply(this, arguments);

        var proto = options.registry.company_data.prototype;

        if (proto.__link_deferred === undefined) {
            proto.__link_deferred = $.Deferred();
            return ajax.jsonRpc("/web/session/get_session_info", "call").then(function (session) {
                return (new Model("res.users")).get_func("read")(session.uid, ["company_id"]).then(function (res) {
                    proto.__link_deferred.resolve(
                        "/web#action=base.action_res_company_form&view_type=form&id=" + (res && res[0] && res[0].company_id[0] || 1)
                    );
                });
            });
        }
    },

    on_focus: function () {
        this._super.apply(this, arguments);

        var proto = options.registry.company_data.prototype;

        Dialog.confirm(null, _t("Do you want to edit the company data ?"), {
            confirm_callback: function () {
                editor.editor_bar.save_without_reload().then(function () {
                    proto.__link_deferred.then(function (link) {
                        window.location.href = link;
                    });
                });
            },
        });
    },
});

options.registry.slider = options.Class.extend({
    drop_and_build_snippet: function () {
        this.id = "myCarousel" + new Date().getTime();
        this.$target.attr("id", this.id);
        this.$target.find("[data-slide]").attr("data-cke-saved-href", "#" + this.id);
        this.$target.find("[data-target]").attr("data-target", "#" + this.id);
        this.rebind_event();
    },
    on_clone: function ($clone) {
        var id = "myCarousel" + new Date().getTime();
        $clone.attr("id", id);
        $clone.find("[data-slide]").attr("href", "#" + id);
        $clone.find("[data-slide-to]").attr("data-target", "#" + id);
    },
    // rebind event to active carousel on edit mode
    rebind_event: function () {
        var self = this;
        this.$target.find('.carousel-indicators [data-slide-to]').off('click').on('click', function () {
            self.$target.carousel(+$(this).data('slide-to')); });
    },
    clean_for_save: function () {
        this._super();
        this.$target.find(".item").removeClass("next prev left right active")
            .first().addClass("active");
        this.$target.find('.carousel-indicators').find('li').removeClass('active')
            .first().addClass("active");
    },
    start : function () {
        this._super.apply(this, arguments);
        this.$target.carousel({interval: false});
        this.id = this.$target.attr("id");
        this.$inner = this.$target.find('.carousel-inner');
        this.$indicators = this.$target.find('.carousel-indicators');
        this.$target.carousel('pause');
        this.rebind_event();
    },
    add_slide: function (type) {
        if(type !== "click") return;

        var self = this;
        var cycle = this.$inner.find('.item').length;
        var $active = this.$inner.find('.item.active, .item.prev, .item.next').first();
        var index = $active.index();
        this.$target.find('.carousel-control, .carousel-indicators').removeClass("hidden");
        this.$indicators.append('<li data-target="#' + this.id + '" data-slide-to="' + cycle + '"></li>');

        // clone the best candidate from template to use new features
        var $snippets = this.buildingBlock.$snippets;
        //since saas-6, all snippets must start by s_
        var selection = this.$target.closest('[class*="s_"');
        if (_.isUndefined(selection)) {
            var point = 0;
            var className = _.compact(this.$target.attr("class").split(" "));
            $snippets.find('.oe_snippet_body').each(function () {
                var len = _.intersection(_.compact(this.className.split(" ")), className).length;
                if (len > point) {
                    point = len;
                    selection = this;
                }
            });
        }
        else {
            var s_class = selection.attr('class').split(' ').filter(function (o) { return _.str.startsWith(o, "s_"); })[0];
            selection = $snippets.find("." + s_class);
        }
        var $clone = $(selection).find('.item:first').clone();

        // insert
        $clone.removeClass('active').insertAfter($active);
        setTimeout(function () {
            self.$target.carousel().carousel(++index);
            self.rebind_event();
        },0);
        return $clone;
    },
    remove_slide: function (type) {
        if (type !== "click" || this.remove_process) return;
        var self = this;

        var $items = this.$inner.find('.item');
        var cycle = $items.length - 1;
        var $active = $items.filter('.active');
        var index = $active.index();

        if (cycle > 0) {
            this.remove_process = true;
            this.$target.on('slid.bs.carousel.slide_removal', function (event) {
                $active.remove();
                self.$indicators.find("li:last").remove();
                self.$target.off('slid.bs.carousel.slide_removal');
                self.rebind_event();
                self.remove_process = false;
                if (cycle === 1) {
                    self.$target.find('.carousel-control, .carousel-indicators').addClass("hidden");
                }
            });
            _.defer(function () {
                self.$target.carousel(index > 0 ? --index : cycle);
            });
        }
    },
    interval : function (type, value) {
        this.$target.attr("data-interval", value);
    },
    set_active: function () {
        this.$el.find('li[data-interval]').removeClass("active")
            .filter('li[data-interval='+this.$target.attr("data-interval")+']').addClass("active");
    },
});

options.registry.carousel = options.registry.slider.extend({
    getSize: function () {
        this.grid = this._super();
        this.grid.size = 8;
        return this.grid;
    },
    clean_for_save: function () {
        this._super();
        this.$target.removeClass('oe_img_bg ' + this._class).css("background-image", "");
    },
    load_style_options : function () {
        this._super();
        $(".snippet-option-size li[data-value='']").remove();
    },
    start : function () {
        var self = this;
        this._super.apply(this, arguments);

        // set background and prepare to clean for save
        this.$target.on('slid.bs.carousel', function () {
            self.$target.carousel("pause");
            if (!self.editor) return;

            _.each(["background", "background_position", "colorpicker"], function (opt_name) {
                var s_option = self.editor.styles[opt_name];
                if (!s_option) return;

                s_option.$target = self.$target.find(".item.active");
                s_option.set_active();
                s_option.$target.trigger("snippet-option-change", [s_option]);
                if (opt_name === 'background') {
                    s_option.bind_bg_events();
                }
            });
        });
        this.$target.trigger('slid.bs.carousel');
    },
    // rebind event to active carousel on edit mode
    rebind_event: function () {
        var self = this;
        this.$target.find('.carousel-control').off('click').on('click', function () {
            self.$target.carousel($(this).data('slide'));
        });
        this._super.apply(this, arguments);

        /* Fix: backward compatibility saas-3 */
        this.$target.find('.item.text_image, .item.image_text, .item.text_only').find('.container > .carousel-caption > div, .container > img.carousel-image').attr('contentEditable', 'true');
    },
});

options.registry["margin-x"] = options.registry.marginAndResize.extend({
    preventChildPropagation: true,

    getSize: function () {
        this.grid = this._super();
        var width = this.$target.parents(".row:first").first().outerWidth();

        var grid = [1,2,3,4,5,6,7,8,9,10,11,12];
        this.grid.e = [_.map(grid, function (v) {return 'col-md-'+v;}), _.map(grid, function (v) {return width/12*v;})];

        grid = [-12,-11,-10,-9,-8,-7,-6,-5,-4,-3,-2,-1,0,1,2,3,4,5,6,7,8,9,10,11];
        this.grid.w = [_.map(grid, function (v) {return 'col-md-offset-'+v;}), _.map(grid, function (v) {return width/12*v;}), 12];

        return this.grid;
    },
    on_clone: function ($clone, options) {
        // Below condition is added to remove offset of target element only
        // and not its children to avoid design alteration of a container / block.
        if (options.isCurrent) {
            var _class = $clone.attr("class").replace(/\s*(col-lg-offset-|col-md-offset-)([0-9-]+)/g, '');
            $clone.attr("class", _class);
        }
        return false;
    },
    on_resize: function (compass, beginClass, current) {
        if (compass === 'w') {
            // don't change the right border position when we change the offset (replace col size)
            var beginCol = Number(beginClass.match(/col-md-([0-9]+)|$/)[1] || 0);
            var beginOffset = Number(beginClass.match(/col-md-offset-([0-9-]+)|$/)[1] || beginClass.match(/col-lg-offset-([0-9-]+)|$/)[1] || 0);
            var offset = Number(this.grid.w[0][current].match(/col-md-offset-([0-9-]+)|$/)[1] || 0);
            if (offset < 0) {
                offset = 0;
            }
            var colSize = beginCol - (offset - beginOffset);
            if (colSize <= 0) {
                colSize = 1;
                offset = beginOffset + beginCol - 1;
            }
            this.$target.attr("class",this.$target.attr("class").replace(/\s*(col-lg-offset-|col-md-offset-|col-md-)([0-9-]+)/g, ''));

            this.$target.addClass('col-md-' + (colSize > 12 ? 12 : colSize));
            if (offset > 0) {
                this.$target.addClass('col-md-offset-' + offset);
            }
        }
        this._super(compass, beginClass, current);
    },
});

options.registry.parallax = options.Class.extend({
    getSize: function () {
        this.grid = this._super.apply(this, arguments);
        this.grid.size = 8;
        return this.grid;
    },
    on_resize: function () {
        this._refresh();
    },
    _refresh: function () {
        this.$target.data("snippet-view").set_values();
    },
    start: function () {
        this._super.apply(this, arguments);
        if (!this.$target.data("snippet-view")) {
            this.$target.data("snippet-view", new animation.registry.parallax(this.$target));
        }
        this.scroll();

        this._refresh_callback = this._refresh.bind(this);
        this.buildingBlock.$el.on("snippet-dropped snippet-activated", this._refresh_callback);
        this.$target.on('snippet-option-change snippet-option-preview', this._refresh_callback);
    },
    scroll: function (type, value) {
        this.$target.attr("data-scroll-background-ratio", value);
        this._refresh();
    },
    set_active: function () {
        this.$el.find('[data-scroll]').removeClass("active")
            .filter('[data-scroll="' + (this.$target.attr('data-scroll-background-ratio') || 0) + '"]').addClass("active");
    },
    clean_for_save: function () {
        this._super.apply(this, arguments);
        this.$target.css("background-position", '').css("background-attachment", '');
    },
    on_move: function () {
        this._super.apply(this, arguments);
        this._refresh();
    },
    on_remove: function () {
        this._super.apply(this, arguments);
        this.$target.off("snippet-option-change snippet-option-preview", this._refresh_callback);
        this.buildingBlock.$el.off("snippet-dropped snippet-activated", this._refresh_callback);
    },
});

options.registry.ul = options.Class.extend({
    start: function () {
        var self = this;
        this._super();
        this.$target.data("snippet-view", new animation.registry.ul(this.$target, true));
        this.$target.on('mouseup', '.o_ul_toggle_self, .o_ul_toggle_next', function () {
            setTimeout(function () {
                self.buildingBlock.cover_target(self.$overlay, self.$target);
            },0);
        });
    },
    reset_ul: function () {
        this.$target.find('.o_ul_toggle_self, .o_ul_toggle_next').remove();

        this.$target.find('li:has(>ul,>ol)').map(function () {
            // get if the li contain a text label
            var texts = _.filter(_.toArray(this.childNodes), function (a) { return a.nodeType == 3;});
            if (!texts.length || !texts.reduce(function (a,b) { return a.textContent + b.textContent;}).match(/\S/)) {
                return;
            }
            $(this).children('ul,ol').addClass('o_close');
            return $(this).children(':not(ul,ol)')[0] || this;
        })
        .prepend('<a href="#" class="o_ul_toggle_self fa" />');

        var $li = this.$target.find('li:has(+li:not(>.o_ul_toggle_self)>ul, +li:not(>.o_ul_toggle_self)>ol)');
        $li.map(function () { return $(this).children()[0] || this; })
            .prepend('<a href="#" class="o_ul_toggle_next fa" />');
        $li.removeClass('o_open').next().addClass('o_close');

        this.$target.find("li").removeClass('o_open').css('list-style', '');
        this.$target.find("li:has(.o_ul_toggle_self, .o_ul_toggle_next), li:has(>ul,>ol):not(:has(>li))").css('list-style', 'none');
    },
    clean_for_save: function () {
        this._super();
        if (!this.$target.hasClass('o_ul_folded')) {
            this.$target.find(".o_close").removeClass("o_close");
        }
        this.$target.find("li:not(:has(>ul))").css('list-style', '');
    },
    toggle_class: function (type, value, $li) {
        this._super(type, value, $li);
        this.$target.data("snippet-view").stop();
        this.reset_ul();
        this.$target.find("li:not(:has(>ul))").css('list-style', '');
        this.$target.data("snippet-view", new animation.registry.ul(this.$target, true));
    }
});

options.registry.collapse = options.Class.extend({
    start: function () {
        var self = this;
        this._super();
        this.$target.on('shown.bs.collapse hidden.bs.collapse', '[role="tabpanel"]', function () {
            self.buildingBlock.cover_target(self.$overlay, self.$target);
        });
    },
    create_ids: function ($target) {
        var time = new Date().getTime();
        var $tab = $target.find('[data-toggle="collapse"]');

        // link to the parent group

        var $tablist = $target.closest('.panel-group');
        var tablist_id = $tablist.attr("id");
        if (!tablist_id) {
            tablist_id = "myCollapse" + time;
            $tablist.attr("id", tablist_id);
        }
        $tab.attr('data-parent', "#"+tablist_id);
        $tab.data('parent', "#"+tablist_id);

        // link to the collapse

        var $panel = $target.find('.panel-collapse');
        var panel_id = $panel.attr("id");
        if (!panel_id) {
            while($('#'+(panel_id = "myCollapseTab" + time)).length) {
                time++;
            }
            $panel.attr("id", panel_id);
        }
        $tab.attr('data-target', "#"+panel_id);
        $tab.data('target', "#"+panel_id);
    },
    drop_and_build_snippet: function () {
        this._super();
        this.create_ids(this.$target);
    },
    on_clone: function ($clone) {
        this._super.apply(this, arguments);
        $clone.find('[data-toggle="collapse"]').removeAttr('data-target').removeData('target');
        $clone.find('.panel-collapse').removeAttr('id');
        this.create_ids($clone);
    },
    on_move: function () {
        this._super();
        this.create_ids(this.$target);
        var $panel = this.$target.find('.panel-collapse').removeData('bs.collapse');
        if ($panel.attr('aria-expanded') === 'true') {
            $panel.closest('.panel-group').find('.panel-collapse[aria-expanded="true"]')
                .filter(function () {return this !== $panel[0];})
                .collapse('hide')
                .one('hidden.bs.collapse', function () {
                    $panel.trigger('shown.bs.collapse');
                });
        }
    }
});

return options;
});


odoo.define('website.rte.summernote', function (require) {
'use strict';

var core = require('web.core');
require('web_editor.rte.summernote');

var eventHandler = $.summernote.eventHandler;
var renderer = $.summernote.renderer;
var tplIconButton = renderer.getTemplate().iconButton;
var _t = core._t;

var fn_tplPopovers = renderer.tplPopovers;
renderer.tplPopovers = function (lang, options) {
    var $popover = $(fn_tplPopovers.call(this, lang, options));
    $popover.find('.note-image-popover .btn-group:has([data-value="img-thumbnail"])').append(
        tplIconButton('fa fa-object-ungroup', {
            title: _t('Transform the picture (click twice to reset transformation)'),
            event: 'transform',
        }));
    return $popover;
};


$.summernote.pluginEvents.transform = function (event, editor, layoutInfo, sorted) {
    var $selection = layoutInfo.handle().find('.note-control-selection');
    var $image = $($selection.data('target'));

    if($image.data('transfo-destroy')) {
        $image.removeData('transfo-destroy');
        return;
    }

    $image.transfo();

    var mouseup = function (event) {
        $('.note-popover button[data-event="transform"]').toggleClass('active', $image.is('[style*="transform"]'));
    };
    $(document).on('mouseup', mouseup);

    var mousedown = function (event) {
        if (!$(event.target).closest('.transfo-container').length) {
            $image.transfo("destroy");
            $(document).off('mousedown', mousedown).off('mouseup', mouseup);
        }
        if ($(event.target).closest('.note-popover').length) {
            $image.data('transfo-destroy', true).attr("style", ($image.attr("style") || '').replace(/[^;]*transform[\w:]*;?/g, ''));
        }
        $image.trigger('content_changed');
    };
    $(document).on('mousedown', mousedown);
};

var fn_boutton_update = eventHandler.modules.popover.button.update;
eventHandler.modules.popover.button.update = function ($container, oStyle) {
    fn_boutton_update.call(this, $container, oStyle);
    $container.find('button[data-event="transform"]')
        .toggleClass('active', $(oStyle.image).is('[style*="transform"]'))
        .toggleClass('hidden', !$(oStyle.image).is('img'));
};
});
