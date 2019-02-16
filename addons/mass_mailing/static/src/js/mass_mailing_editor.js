odoo.define('mass_mailing.editor', function (require) {
"use strict";

var Model = require('web.Model');
var rte = require('web_editor.rte');
var web_editor = require('web_editor.editor');
var options = require('web_editor.snippets.options');
var snippets_editor = require('web_editor.snippet.editor');

// Snippet option for resizing  image and column width inline like excel
options.registry["width-x"] = options.Class.extend({
    start: function () {
        this.container_width = 600;
        var parent = this.$target.closest('[data-max-width]');
        if( parent.length ){
            this.container_width = parseInt(parent.attr('data-max-width'));
        } 
        var self = this;
        var offset, sib_offset, target_width, sib_width;
        this.is_image = false;
        this._super();

        this.$overlay.find(".oe_handle.e, .oe_handle.w").removeClass("readonly");
        if( this.$target.is('img')){
            this.$overlay.find(".oe_handle.w").addClass("readonly");
            this.$overlay.find(".oe_snippet_remove, .oe_snippet_move, .oe_snippet_clone").addClass("hidden");
            this.is_image=true;
        }

        this.$overlay.find(".oe_handle").on('mousedown', function (event){
            event.preventDefault();
            var $handle = $(this);
            var compass = false;

            _.each(['n', 's', 'e', 'w' ], function(handler) {
                if ($handle.hasClass(handler)) { compass = handler; }
            });
            if(self.is_image){ compass = "image"; }
            self.buildingBlock.editor_busy = true;

            var $body = $(document.body);

            var body_mousemove = function (event){
                event.preventDefault();
                offset = self.$target.offset().left;
                target_width = self.get_max_width(self.$target);
                if (compass === 'e' && self.$target.next().offset()) {
                    sib_width = self.get_max_width(self.$target.next());
                    sib_offset = self.$target.next().offset().left;
                    self.change_width(event, self.$target, target_width, offset ,'plus');
                    self.change_width(event, self.$target.next(), sib_width, sib_offset ,'minus');
                }
                if (compass === 'w' && self.$target.prev().offset()) {
                    sib_width = self.get_max_width(self.$target.prev());
                    sib_offset = self.$target.prev().offset().left;
                    self.change_width(event, self.$target, target_width, offset ,'minus');
                    self.change_width(event, self.$target.prev(), sib_width, sib_offset, 'plus');
                }
                if (compass === 'image'){
                    self.change_width(event, self.$target, target_width, offset ,'plus');
                }
            }
            var body_mouseup = function(){
                $body.unbind('mousemove', body_mousemove);
                $body.unbind('mouseup', body_mouseup);
                self.buildingBlock.editor_busy = false;
                self.$target.removeClass("resize_editor_busy");
            };
            $body.mousemove(body_mousemove);
            $body.mouseup(body_mouseup);
        });
    },
    change_width:function(event, target ,target_width, offset, type){
        var self = this;
        if(type == 'plus'){
            var width = event.pageX-offset;
        }else{
            var width = offset + target_width - event.pageX;
        }
        target.css("width", width + "px");
        self.buildingBlock.cover_target(self.$overlay, self.$target);
        return;
    },
    get_int_width: function ($el) {
        var el_width = $el.css('width');
        return parseInt(el_width);
    },
    get_max_width: function ($el) {
        var max_width = 0;
        var self = this;
        _.each($el.siblings(),function(sib){
            max_width +=  self.get_int_width($(sib));
        })
        return this.container_width - max_width;
    },
    on_clone: function ($clone) {
        var clone_index = $(this.$target).index();
        var $table = this.$target.parents('table[data-max-width]');
        if($table.length == 1){
            _.each($table.find('tbody>tr'),function(row){
                var clone_selector = 'td:eq(' + clone_index + ')';
                var $col_to_clone = $(row).find(clone_selector);
                if($col_to_clone.length != 0){
                    $col_to_clone.after($col_to_clone.clone());
                }
            });
        }
        this._super($clone);
        this.buildingBlock.cover_target(this.$overlay, this.$target);
    },
    on_remove: function () {
        var remove_index = $(this.$target).index();
        var $table = this.$target.parents('table[data-max-width]');
        if($table.length == 1){
            _.each($table.find('tbody>tr'),function(row){
                var remove_selector = 'td:eq(' + remove_index + ')';
                $(row).find(remove_selector).remove();
            });
        }
        this._super();
        this.buildingBlock.cover_target(this.$overlay, this.$target);
    },
});


var fn_popover_update = $.summernote.eventHandler.modules.popover.update;
$.summernote.eventHandler.modules.popover.update = function ($popover, oStyle, isAirMode) {
    fn_popover_update.call(this, $popover, oStyle, isAirMode);
    $("span.o_table_handler, div.note-table").remove();
};

web_editor.Class.include({
    start: function () {
        var self = this;
        $('[data-toggle="tooltip"]').tooltip();
        if (location.search.indexOf("enable_editor") !== -1) {
            this.on('rte:start', this, function () {
                $("#choose_template").off("click").on("click", _.bind(self.on_choose_template, self));
                $(".theme_thumbnail [data-snippet-theme]").off("click").on("click", _.bind(self.on_set_snippet_theme, self));
                var $editable = $("#editable_area");
                $editable.html($editable.prop("innerHTML").replace(/^<p[^>]*>\s*<\/p>$/, ''));
            });
            this.on("snippets:ready", this, _.bind(self.display_theme_from_html, self));
        }
        return this._super.apply(this, arguments);
    },
    display_theme_from_html: function () {
        var theme = $("#editable_area [data-snippet-theme]").data("snippet-theme");
        if (theme) {
            $("#choose_template").show();
            this.set_snippet_theme(theme);
        } else {
            $("#choose_template").hide();
            this.on_choose_template();
        }
        var mailing_model = JSON.parse($.deparam(location.search).datarecord).mailing_model;
        if (mailing_model) {
            this.get_snippet_template( mailing_model );
        }
    },

    on_choose_template: function (event) {
        if (event) {
            $("#choose_template").show();
        }
        var $editable = $("#editable_area");
        $(".o_table_handler").remove();
        $editable.parent().add("#oe_snippets, #templates, .note-popover").toggleClass("hidden");
        $("#choose_template").children().toggleClass("hidden");
        $("body").trigger("resize");
        $(window.top).trigger('resize');
        setTimeout(function () {
            $(".note-popover").toggleClass("hidden", $("#templates").is(":visible"));
        },0);
    },
    on_set_snippet_template: function (event) {
        var $editable = $("#editable_area");
        this.rte.historyRecordUndo($editable);
        $editable.html( $(event.target).closest(".theme_thumbnail").find(".js_content").html() );
        $editable.parent().add("#oe_snippets, #templates, .note-popover").toggleClass("hidden");
        $("#choose_template").children().toggleClass("hidden");
        setTimeout(function () {
            $("body").trigger("resize");
            $("body")[0].scrollTop = 0;
        },0);
        event.preventDefault();
    },
    on_set_snippet_theme: function (event) {
        this.set_snippet_theme($(event.target).data("snippet-theme"));
        this.on_choose_template(event);
        event.preventDefault();
    },
    set_snippet_theme: function (theme) {
        $("#o_left_bar .o_panel_body > div").addClass("hidden");
        $("#o_left_bar .o_panel_body > div."+theme).removeClass("hidden");
        $("#editable_area").trigger("content_changed");
    },
    get_snippet_template: function (mailing_model) {
        var self = this;
        var domain = [['model', '=', mailing_model]];
        return new Model('mail.template').call('search_read', [domain]).then(function (datas) {
            var $template = $("#templates > div:last").addClass("hidden");
            var $tclone = $template.find("> div > div:first");
            $tclone.siblings().remove();
            _.each(datas, function (data) {
                if (!data.body_html) {
                    return;
                }
                $template.removeClass("hidden");
                var $clone = $tclone.clone().removeClass("hidden");
                $clone.find("p:first").html(data.name);
                $clone.find(".template_preview").html(data.body_html);
                $tclone.after($clone);
            });

            $(".js_template_set").off("click").on("click", _.bind(self.on_set_snippet_template, self));
        });
    }
});

snippets_editor.Class.include({
    _get_snippet_url: function () {
        return snippets_url;
    },
    clean_for_save: function () {
        this._super();
        var $editable = $("#editable_area");
        var theme = ($("#o_left_bar .o_panel_body > div:not(.hidden)").attr("class") || "").replace(/^\s*|\s*o_mail_block[^\s]+\s*|\s*oe_snippet\s*|\s*ui-draggable\s*|\s*$/g, '');
        var $theme = $("#editable_area [data-snippet-theme]").removeAttr("data-snippet-theme").removeData("snippet-theme");
        $editable.children().first().attr("data-snippet-theme", theme);
        // before jQuery 3, google chrome needs the `:not(:has(:visible))` part
        $editable.find(":not(br):hidden:not(:has(:visible))").remove();
    },
});

var _set_value = window.top.odoo[callback+"_updown"];
var odoo_top = window.top.odoo;
window.top.odoo[callback+"_updown"] = function (value, fields_values, field_name) {
    if (!window || window.closed) {
        delete odoo_top[callback+"_updown"];
        return;
    }

    var $editable = $("#editable_area");
    var _val = $editable.prop("innerHTML");
    var editor_enable = $('body').hasClass('editor_enable');
    value = value || "";
    
    if(value !==_val) {
        if (editor_enable) {
            if (value !== fields_values[field_name]) {
                rte.history.recordUndo($editable);
            }
            snippets_editor.instance.make_active(false);
        }
        
        if (value.indexOf('on_change_model_and_list') === -1) {

            $editable.html(value);

            if (editor_enable) {
                web_editor.editor_bar.display_theme_from_html();

                if (value !== fields_values[field_name]) {
                    $editable.trigger("content_changed");
                }
            }
        }
    }

    if (fields_values.mailing_model && web_editor.editor_bar) {
        web_editor.editor_bar.get_snippet_template(fields_values.mailing_model);
        if (value.indexOf('on_change_model_and_list') !== -1) {
            odoo_top[callback+"_downup"](_val);
        }
    }
};


if ($("#editable_area").html().indexOf('on_change_model_and_list') !== -1) {
    $("#editable_area").empty();
}

// Adding compatibility for the outlook compliance of mailings.
// Commit of such compatibility : a14f89c8663c9cafecb1cc26918055e023ecbe42
options.registry.background.include({
    start: function() {
        this._super();
        var $table_target = this.$target.find('table:first');
        if ($table_target) {
            this.$target = $table_target;
        }
    }
});
});
