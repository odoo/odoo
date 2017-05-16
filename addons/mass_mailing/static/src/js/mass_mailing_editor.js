odoo.define('mass_mailing.editor', function (require) {
"use strict";

var ajax = require("web.ajax");
var core = require("web.core");
var rte = require('web_editor.rte');
var web_editor = require('web_editor.editor');
var options = require('web_editor.snippets.options');
var snippets_editor = require('web_editor.snippet.editor');

var $editable_area = $("#editable_area");
var odoo_top = window.top.odoo;

// Snippet option for resizing  image and column width inline like excel
options.registry["width-x"] = options.Class.extend({
    start: function () {
        this.container_width = this.$target.parent().closest("td, table, div").width();

        var self = this;
        var offset, sib_offset, target_width, sib_width;
        var $body = $(document.body);
        this.is_image = false;
        this._super.apply(this, arguments);

        this.$overlay.find(".oe_handle.e, .oe_handle.w").removeClass("readonly");
        if (this.$target.is("img")) {
            this.$overlay.find(".oe_handle.w").addClass("readonly");
            this.$overlay.find(".oe_snippet_move, .oe_snippet_clone").addClass("hidden");
            this.is_image=true;
        }

        this.$overlay.find(".oe_handle").on('mousedown', function (event) {
            event.preventDefault();
            var $handle = $(this);
            var compass = false;

            _.each(['n', 's', 'e', 'w' ], function(handler) {
                if ($handle.hasClass(handler)) { compass = handler; }
            });
            if (self.is_image) { compass = "image"; }
            self.buildingBlock.editor_busy = true;

            $body.on("mousemove.mass_mailing_width_x", function (event) {
                event.preventDefault();
                offset = self.$target.offset().left;
                target_width = self.get_max_width(self.$target);
                if (compass === 'e' && self.$target.next().offset()) {
                    sib_width = self.get_max_width(self.$target.next());
                    sib_offset = self.$target.next().offset().left;
                    self.change_width(event, self.$target, target_width, offset, true);
                    self.change_width(event, self.$target.next(), sib_width, sib_offset, false);
                }
                if (compass === 'w' && self.$target.prev().offset()) {
                    sib_width = self.get_max_width(self.$target.prev());
                    sib_offset = self.$target.prev().offset().left;
                    self.change_width(event, self.$target, target_width, offset, false);
                    self.change_width(event, self.$target.prev(), sib_width, sib_offset, true);
                }
                if (compass === 'image') {
                    self.change_width(event, self.$target, target_width, offset, true);
                }
            });
            $body.on("mouseup.mass_mailing_width_x", function () {
                $body.off('.mass_mailing_width_x');
                self.buildingBlock.editor_busy = false;
                self.$target.removeClass("resize_editor_busy");
            });
        });
    },
    change_width: function (event, target, target_width, offset, grow) {
        target.css("width", grow ? (event.pageX - offset) : (offset + target_width - event.pageX));
        this.buildingBlock.cover_target(this.$overlay, this.$target);
    },
    get_int_width: function (el) {
        return parseInt($(el).css("width"), 10);
    },
    get_max_width: function ($el) {
        return this.container_width - _.reduce(_.map($el.siblings(), this.get_int_width), function (memo, w) { return memo + w; });
    },
    on_focus: function () {
        this._super.apply(this, arguments);

        if (this.$target.is("td, th")) {
            this.$overlay.find(".oe_handle.e, .oe_handle.w").toggleClass("readonly", this.$target.siblings().length === 0);
        }
    },
});

options.registry.table_item = options.Class.extend({
    on_clone: function ($clone) {
        this._super.apply(this, arguments);

        // If we cloned a td or th element...
        if (this.$target.is("td, th")) {
            // ... and that the td or th element was alone on its row ...
            if (this.$target.siblings().length === 1) {
                var $tr = $clone.parent();
                $tr.clone().empty().insertAfter($tr).append($clone); // ... move the clone in a new row instead
                return;
            }

            // ... if not, if the clone neighbor is an empty cell, remove this empty cell (like if the clone content had been put in that cell)
            var $next = $clone.next();
            if ($next.length && $next.text().trim() === "") {
                $next.remove();
                return;
            }

            // ... if not, insert an empty col in each other row, at the index of the clone
            var width = $clone.width();
            var $trs = this.$target.closest("table").children("thead, tbody, tfoot").addBack().children("tr").not(this.$target.parent());
            _.each($trs.children(":nth-child(" + this.$target.index() + ")"), function (col) {
                $(col).after($("<td/>", {style: "width: " + width + "px;"}));
            });
        }
    },
    on_remove: function () {
        this._super.apply(this, arguments);

        // If we are removing a td or th element which was not alone on its row ...
        if (this.$target.is("td, th") && this.$target.siblings().length > 0) {
            var $trs = this.$target.closest("table").children("thead, tbody, tfoot").addBack().children("tr").not(this.$target.parent());
            if ($trs.length) { // ... if there are other rows in the table ...
                var $last_tds = $trs.children(":last-child");
                if (_.reduce($last_tds, function (memo, td) { return memo + (td.innerHTML || ""); }, "").trim() === "") {
                    $last_tds.remove(); // ... remove the potential full empty column in the table
                } else {
                    this.$target.parent().append("<td/>"); // ... else, if there is no full empty column, append an empty col in the current row
                }
            }
        }
    },
});

var fn_popover_update = $.summernote.eventHandler.modules.popover.update;
$.summernote.eventHandler.modules.popover.update = function ($popover, oStyle, isAirMode) {
    fn_popover_update.call(this, $popover, oStyle, isAirMode);
    $("span.o_table_handler, div.note-table").remove();
};

ajax.loadXML("/mass_mailing/static/src/xml/mass_mailing.xml", core.qweb);

snippets_editor.Class.include({
    _get_snippet_url: function () {
        var url = (typeof snippets_url !== "undefined" ? window["snippets_url"] : this._super.apply(this, arguments));
        return url;
    },
    compute_snippet_templates: function (html) {
        var self = this;
        var ret = this._super.apply(this, arguments);

        var $themes = this.$("#email_designer_themes").children();
        if ($themes.length === 0) return ret;

        /**
         * Initialize theme parameters.
         */
        var all_classes = "";
        var themes_params = _.map($themes, function (theme) {
            var $theme = $(theme);
            var name = $theme.data("name");
            var classname = "o_" + name + "_theme";
            all_classes += " " + classname;
            var images_info = _.defaults($theme.data("imagesInfo") || {}, {all: {}});
            _.each(images_info, function (info) {
                info = _.defaults(info, images_info.all, {module: "mass_mailing", format: "jpg"});
            });
            return {
                name: name,
                className: classname || "",
                img: $theme.data("img") || "",
                template: $theme.html().trim(),
                get_image_info: function (filename) {
                    if (images_info[filename]) {
                        return images_info[filename];
                    }
                    return images_info.all;
                }
            };
        });
        $themes.parent().remove();

        var $body = $(document.body);
        var $snippets = this.$(".oe_snippet");
        var $snippets_menu = this.$el.find("#snippets_menu");

        /**
         * Create theme selection screen and check if it must be forced opened.
         * Reforce it opened if the last snippet is removed.
         */
        var $dropdown = $(core.qweb.render("mass_mailing.theme_selector", {
            themes: themes_params
        }));
        var first_choice;
        check_if_must_force_theme_choice();

        /**
         * Add proposition to install enterprise themes if not installed.
         */
        var $mail_themes_upgrade = $dropdown.find(".o_mass_mailing_themes_upgrade");
        $mail_themes_upgrade.on("click", "> a", function (e) {
            e.stopImmediatePropagation();
            e.preventDefault();
            odoo_top[window.callback+"_do_action"]("mass_mailing.action_mass_mailing_configuration");
        });

        /**
         * Switch theme when a theme button is hovered. Confirm change if the theme button
         * is pressed.
         */
        var selected_theme = false;
        $dropdown.on("mouseenter", "li > a", function (e) {
            if (first_choice) return;
            e.preventDefault();
            var theme_params = themes_params[$(e.currentTarget).parent().index()];
            switch_theme(theme_params);
        });
        $dropdown.on("click", "li > a", function (e) {
            e.preventDefault();
            var theme_params = themes_params[$(e.currentTarget).parent().index()];
            if (first_choice) {
                switch_theme(theme_params);
                $body.removeClass("o_force_mail_theme_choice");
                first_choice = false;

                if ($mail_themes_upgrade.length) {
                    $dropdown.remove();
                    $snippets_menu.empty();
                }
            }

            switch_images(theme_params, $snippets);

            selected_theme = theme_params;

            // Notify form view
            odoo_top[window.callback+"_downup"]($editable_area.addClass("o_dirty").html());
        });

        /**
         * If the user opens the theme selection screen, indicates which one is active and
         * saves the information...
         * ... then when the user closes check if the user confirmed its choice and restore
         * previous state if this is not the case.
         */
        $dropdown.on("shown.bs.dropdown", function () {
            check_selected_theme();
            $dropdown.find("li").removeClass("selected").filter(function () {
                return ($(this).has(".o_thumb[style=\""+ "background-image: url(" + (selected_theme && selected_theme.img) + "_small.png)"+ "\"]").length > 0);
            }).addClass("selected");
        });
        $dropdown.on("hidden.bs.dropdown", function () {
            switch_theme(selected_theme);
        });

        /**
         * On page load, check the selected theme and force switching to it (body needs the
         * theme style for its edition toolbar).
         */
        check_selected_theme();
        $body.addClass(selected_theme.className);
        switch_images(selected_theme, $snippets);

        $dropdown.insertAfter($snippets_menu);

        return ret;

        function check_if_must_force_theme_choice() {
            first_choice = editable_area_is_empty();
            $body.toggleClass("o_force_mail_theme_choice", first_choice);
        }

        function editable_area_is_empty($layout) {
            $layout = $layout || $editable_area.find(".o_layout");
            var $mail_wrapper = $layout.children(".o_mail_wrapper");
            var $mail_wrapper_content = $mail_wrapper.find('.o_mail_wrapper_td');
            if (!$mail_wrapper_content.length) { // compatibility
                $mail_wrapper_content = $mail_wrapper;
            }
            return (
                $editable_area.html().trim() === ""
                || ($layout.length > 0 && ($layout.html().trim() === "" || $mail_wrapper_content.length > 0 && $mail_wrapper_content.html().trim() === ""))
            );
        }

        function check_selected_theme() {
            var $layout = $editable_area.find(".o_layout");
            if ($layout.length === 0) {
                selected_theme = false;
            } else {
                _.each(themes_params, function (theme_params) {
                    if ($layout.hasClass(theme_params.className)) {
                        selected_theme = theme_params;
                    }
                });
            }
        }

        function switch_images(theme_params, $container) {
            if (!theme_params) return;
            $container.find("img").each(function () {
                var $img = $(this);
                var src = $img.attr("src");

                var m = src.match(/^\/web\/image\/\w+\.s_default_image_(?:theme_[a-z]+_)?(.+)$/);
                if (!m) {
                    m = src.match(/^\/\w+\/static\/src\/img\/(?:theme_[a-z]+\/)?s_default_image_(.+)\.[a-z]+$/);
                }
                if (!m) return;

                var file = m[1];
                var img_info = theme_params.get_image_info(file);

                if (img_info.format) {
                    src = "/" + img_info.module + "/static/src/img/theme_" + theme_params.name + "/s_default_image_" + file + "." + img_info.format;
                } else {
                    src = "/web/image/" + img_info.module + ".s_default_image_theme_" + theme_params.name + "_" + file;
                }

                $img.attr("src", src);
            });
        }

        function switch_theme(theme_params) {
            if (!theme_params || switch_theme.last === theme_params) return;
            switch_theme.last = theme_params;

            $body.removeClass(all_classes).addClass(theme_params.className);
            switch_images(theme_params, $editable_area);

            var $old_layout = $editable_area.find(".o_layout");
            // This wrapper structure is the only way to have a responsive and
            // centered fixed-width content column on all mail clients
            var $new_wrapper = $('<table/>', {class: 'o_mail_wrapper'});
            var $new_wrapper_content = $("<td/>", {class: 'o_mail_no_resize o_mail_wrapper_td oe_structure'});
            $new_wrapper.append($('<tr/>').append(
                $("<td/>", {class: 'o_mail_no_resize'}),
                $new_wrapper_content,
                $("<td/>", {class: 'o_mail_no_resize'})
            ));
            var $new_layout = $("<div/>", {"class": "o_layout " + theme_params.className}).append($new_wrapper);

            var $contents;
            if (first_choice) {
                $contents = theme_params.template;
            } else if ($old_layout.length) {
                $contents = ($old_layout.hasClass("oe_structure") ? $old_layout : $old_layout.find(".oe_structure").first()).contents();
            } else {
                $contents = $editable_area.contents();
            }

            $editable_area.empty().append($new_layout);
            $new_wrapper_content.append($contents);
            $old_layout.remove();

            if (first_choice) {
                self.add_default_snippet_text_classes($new_wrapper_content);
            }
            self.show_blocks();
        }
    },
});

var callback = window ? window["callback"] : undefined;
odoo_top[callback+"_updown"] = function (value, fields_values, field_name) {
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
                if (value !== fields_values[field_name]) {
                    $editable.trigger("content_changed");
                }
            }
        }
    }

    if (fields_values.mailing_model && web_editor.editor_bar) {
        if (value.indexOf('on_change_model_and_list') !== -1) {
            odoo_top[callback+"_downup"](_val);
        }
    }
};

if ($editable_area.html().indexOf('on_change_model_and_list') !== -1) {
    $editable_area.empty();
}
});
