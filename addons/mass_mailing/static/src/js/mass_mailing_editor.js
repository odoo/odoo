odoo.define('mass_mailing.editor', function (require) {
"use strict";

require('web.dom_ready');
var ajax = require('web.ajax');
var core = require('web.core');
var rte = require('web_editor.rte');
var options = require('web_editor.snippets.options');
var snippets_editor = require('web_editor.snippet.editor');
var Dialog = require('web.Dialog');
var session = require('web.session');
var _t = core._t;

var $editable_area = $('#editable_area');
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

            _.each(['n', 's', 'e', 'w' ], function (handler) {
                if ($handle.hasClass(handler)) { compass = handler; }
            });
            if (self.is_image) { compass = "image"; }

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

            $body.one("mouseup", function(){
                $body.off('.mass_mailing_width_x');
            });
        });
    },
    change_width: function (event, target, target_width, offset, grow) {
        target.css("width", grow ? (event.pageX - offset) : (offset + target_width - event.pageX));
        this.trigger_up('cover_update');
    },
    get_int_width: function (el) {
        return parseInt($(el).css("width"), 10);
    },
    get_max_width: function ($el) {
        return this.container_width - _.reduce(_.map($el.siblings(), this.get_int_width), function (memo, w) { return memo + w; });
    },
    onFocus: function () {
        this._super.apply(this, arguments);

        if (this.$target.is("td, th")) {
            this.$overlay.find(".oe_handle.e, .oe_handle.w").toggleClass("readonly", this.$target.siblings().length === 0);
        }
    },
});

options.registry.table_item = options.Class.extend({
    onClone: function () {
        this._super.apply(this, arguments);

        // If we cloned a td or th element...
        if (this.$target.is("td, th")) {
            // ... and that the td or th element was alone on its row ...
            if (this.$target.siblings().length === 1) {
                var $tr = this.$target.parent();
                $tr.clone().empty().insertAfter($tr).append(this.$target); // ... move the clone in a new row instead
                return;
            }

            // ... if not, if the clone neighbor is an empty cell, remove this empty cell (like if the clone content had been put in that cell)
            var $next = this.$target.next();
            if ($next.length && $next.text().trim() === "") {
                $next.remove();
                return;
            }

            // ... if not, insert an empty col in each other row, at the index of the clone
            var width = this.$target.width();
            var $trs = this.$target.closest("table").children("thead, tbody, tfoot").addBack().children("tr").not(this.$target.parent());
            _.each($trs.children(":nth-child(" + this.$target.index() + ")"), function (col) {
                $(col).after($("<td/>", {style: "width: " + width + "px;"}));
            });
        }
    },
    onRemove: function () {
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
    events: _.extend({}, snippets_editor.Class.events, {
        'click .o_mail_switch_theme_btn': '_onSwichThemeButtonClicked',
        'input .o_mail_search_theme_input': '_onSearchEmailTemplate',
        'focusout .o_mail_search_theme_input': '_onSearchEmailTemplateTextFocusOut',
        'click .o_mail_template_image': '_onEmailTemplateImageClicked',
        'click .o_mail_delete_template_btn': '_onDeleteButtonClicked',
        'focusout .o_mail_custom_template_name': '_onTemplateRenameTextboxFocusOut',
        'keypress .o_mail_custom_template_name': '_onTemplateRenameTextboxKeyPress',
        'click .o_mail_save_template_button': '_onSaveButtonClicked',
    }),
     /**
     * @constructor
     */
    init: function() {
        this.first_choice;
        this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    willStart: function() {
        var self = this;
        var defMailTemplate = this._rpc({
            model: 'mail.template',
            method: 'search_read',
            domain: [['model', '=', 'mail.mass_mailing']],
            fields: ['name', 'body_html', 'image', 'create_date', 'create_uid', 'write_date', 'write_uid'],
        });
        var defHasGroup = session.user_has_group('mass_mailing.group_mass_mailing_manager');
        return $.when(this._super.apply(this, arguments), defMailTemplate, defHasGroup).then(function(super_res, mail_template_data, has_group) {
            self.isManager = has_group;
            self.userTemplates = _.filter(mail_template_data, function(r) {return r.create_uid[0] === session.uid});
            self.otherTemplates = _.difference(mail_template_data,  self.userTemplates);
            self.templateData = self.isManager ? mail_template_data : self.userTemplates;
        });
    },

    /**
     * function used to return Saved Template.
     * @param {int} id of saved template.
     * @return {object} object of saved mail template.
     */
    getSavedTemplate: function(template_id) {
        return _.findWhere(this.templateData, {
            id: template_id
        });
    },
    /**
     * function used to Create, Update and Delete Saved Email Template.
     * @param {string} type of method
     * @param {args} arguments
     * @returns {Deferred}
     */
    queryTemplate: function(method, args) {
        return this._rpc({
            model: 'mail.template',
            method: method,
            args: args,
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * function to switch between Default Email Templates and Saved Email templates.
     * @private
     * @param {Event} ev
     */
    _onSwichThemeButtonClicked: function(e) {
        var $elem = $(e.currentTarget);
        $elem.siblings().removeClass('active');
        if ($elem.data('template_type') === 'default') {
            this.$('.o_mail_search_email_template, .o_mail_custom_email_template_list').addClass('hidden');
            this.$('.o_mail_default_email_templates').removeClass('hidden');
        } else {
            if (!this.$('.o_mail_custom_template_li').length) {
                this.$('.o_mail_no_saved_template_message').removeClass('hidden');
                this.$('.o_mail_search_email_template').remove();
            }
            this.$('.o_mail_search_email_template, .o_mail_custom_email_template_list').removeClass('hidden');
            this.$('.o_mail_default_email_templates').addClass('hidden');
        }
    },
    /**
     * function that search(user-created) custom Email templates.
     * @private
     * @param {Event} ev
     */
    _onSearchEmailTemplate: function(e) {
        var templateName = $(e.currentTarget).val();
        var $totalSavedTemplate = this.$('.o_mail_custom_theme_dropdown .o_mail_custom_template_li');
        var $emailTemplateCategoryTitle = this.$('.o_mail_template_title'); // Email Template Titles (My templates, Other Templates).
        var $noEmailTemplateFoundMsg = this.$('.o_mail_no_saved_template_found_message'); // No Email Template Found Message.
        $emailTemplateCategoryTitle.removeClass('hidden');
        $noEmailTemplateFoundMsg.addClass('hidden');
        if (templateName.trim() === '') {
            $totalSavedTemplate.show();
        } else {
            var $filteredTemplates = $totalSavedTemplate.filter("[data-template_name^='" + templateName + "']");
            $filteredTemplates.show();
            if (!$filteredTemplates.length) {
                $emailTemplateCategoryTitle.addClass('hidden');
                $noEmailTemplateFoundMsg.removeClass('hidden');
            }
            $totalSavedTemplate.not("[data-template_name^='" + templateName + "']").hide();
        }
    },
    /**
     * function that show all Email Templates on focusout of search Email Templates input.
     * @private
     * @param {Event} ev
     */
    _onSearchEmailTemplateTextFocusOut: function(e) {
        $(e.currentTarget).val("");
        this.$('.o_mail_template_title').removeClass('hidden');
        this.$('.o_mail_no_saved_template_found_message').addClass('hidden');
        this.$('.o_mail_custom_theme_dropdown .o_mail_custom_template_li').show();
    },
    /**
     * function to Rendor Saved Email Template on Email Template image click.
     * @private
     * @param {Event} ev
     */
    _onEmailTemplateImageClicked: function(e) {
        e.preventDefault();
        var $elem = $(e.currentTarget);
        $('body.editor_has_snippets').removeClass('o_force_mail_theme_choice');
        this.$('#snippets_menu').empty();
        this.$('.o_mail_default_email_templates').removeClass('hidden');
        this.first_choice = false;
        $editable_area.attr('data-template_id', $elem.closest('.o_mail_custom_template_li').data('template_id'));
        $editable_area.html($elem.closest('.o_mail_custom_template_li').find('.o_mail_custom_template_body_html').html());
    },
    /**
     * function to Delete saved Email Template on Delete Email Template button click.
     * @private
     * @param {Event} ev
     */
    _onDeleteButtonClicked: function(e) {
        var self = this;
        Dialog.confirm(this, _t("Are you sure you want to delete this template ?"), {
            confirm_callback: function() {
                var $selectedTempalte = $(e.currentTarget).closest(".o_mail_custom_template_li");
                var templateId = parseInt($selectedTempalte.data('template_id'));
                var args = [templateId];
                self.queryTemplate('unlink', args).then(function() {
                    var $parent = $selectedTempalte.parent();
                    $selectedTempalte.remove();
                    if (!$parent.find('li').length) {
                        $parent.find('.o_mail_template_title').remove();
                    }
                    self.templateData = _.filter(self.templateData, function(template) {
                        return template.id != templateId
                    });
                    if (!self.$('.o_mail_custom_template_li').length) {
                        self.$('.o_mail_no_saved_template_message').removeClass('hidden');
                    }
                });
            }
        });
    },
    /**
     * function to Rename Saved Email Template on focusout.
     * @private
     * @param {Event} ev
     */
    _onTemplateRenameTextboxFocusOut: function(e) {
        var self = this;
        var $elem = $(e.currentTarget);
        var updatedName = $elem.text().trim();
        var $selectedTempalte = $elem.closest('.o_mail_custom_template_li');
        var templateId = $selectedTempalte.data('template_id');
        var selectedCustomTemplate = this.getSavedTemplate(parseInt(templateId));
        if (selectedCustomTemplate.name != updatedName) {
            var args = [
                [templateId], {
                    'name': updatedName
                }
            ];
            this.queryTemplate('write', args).then(function() {
                $elem.closest('.o_mail_user_saved_templates').append("<div class='fa fa-thumbs-up o_mail_update_template_success text-success'></div>");
                selectedCustomTemplate.name = updatedName;
                $selectedTempalte.attr('data-template_name', updatedName);
                var $successThumb = self.$('.o_mail_update_template_success');
                $successThumb.animate({
                    fontSize: '3em',
                    opacity: '0',
                }, 700);
                _.delay(function() {
                    $successThumb.remove();
                }, 1200);
            });
        }
    },
    /**
     * function to rename saved template on enter key-press.
     * @private
     * @param {Event} ev
     */
    _onTemplateRenameTextboxKeyPress: function(e) {
        if (e.keyCode === 13) {
            e.preventDefault();
            $(e.currentTarget).blur();
        }
    },
    /**
     * function that open a modal to create or update custom email template.
     * @private
     */
    _onSaveButtonClicked: function(e) {
        e.preventDefault();
        var templateId = $editable_area.data('template_id') || this.templateData.length && this.templateData[0].id || false;
        new saveTemplateDialog(this, templateId).open();
    },

    _computeSnippetTemplates: function (html) {
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
                nowrap: !!$theme.data('nowrap'),
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
            themes: themes_params,
            userTemplates: self.userTemplates,
            otherTemplates: self.otherTemplates,
            isManager: self.isManager,
        }));
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
            if (self.first_choice) return;
            e.preventDefault();
            var theme_params = themes_params[$(e.currentTarget).parent().index()];
            switch_theme(theme_params);
        });
        $dropdown.on("click", "li > a", function (e) {
            e.preventDefault();
            $body.find('.o_mail_default_email_templates').removeClass('hidden');
            var theme_params = themes_params[$(e.currentTarget).parent().index()];
            if (self.first_choice) {
                switch_theme(theme_params);
                $body.removeClass("o_force_mail_theme_choice");
                self.first_choice = false;
                $snippets_menu.empty();

                if ($mail_themes_upgrade.length) {
                    $dropdown.remove();
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
            self.first_choice = editable_area_is_empty();
            $body.toggleClass("o_force_mail_theme_choice", self.first_choice);
            if (!$body.hasClass('o_force_mail_theme_choice')) {
                $snippets_menu.empty();
            }
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
            var $new_wrapper, $new_wrapper_content;

            if (theme_params.nowrap) {
                $new_wrapper = $new_wrapper_content = $("<div/>", {"class": "oe_structure"});
            }
            else {
                $new_wrapper = $('<table/>', {class: 'o_mail_wrapper'});
                $new_wrapper_content = $("<td/>", {class: 'o_mail_no_resize o_mail_wrapper_td oe_structure'});
                $new_wrapper.append($('<tr/>').append(
                    $("<td/>", {class: 'o_mail_no_resize'}),
                    $new_wrapper_content,
                    $("<td/>", {class: 'o_mail_no_resize'})
                ));
            }
            var $new_layout = $("<div/>", {"class": "o_layout " + theme_params.className}).append($new_wrapper);

            var $contents;
            if (self.first_choice) {
                $contents = theme_params.template;
            } else if ($old_layout.length) {
                $contents = ($old_layout.hasClass("oe_structure") ? $old_layout : $old_layout.find(".oe_structure").first()).contents();
            } else {
                $contents = $editable_area.contents();
            }

            $editable_area.empty().append($new_layout);
            $new_wrapper_content.append($contents);
            $old_layout.remove();

            if (self.first_choice) {
                self._registerDefaultTexts($new_wrapper_content);
            }
            self._disableUndroppableSnippets();
        }
    },
});

var saveTemplateDialog = Dialog.extend({
    template: "mass_mailing.save_template_dialog",
    events: {
        'change input[type=radio][name=template_option_radio]': '_onChangeDialogRadioOptions',
        'change select.o_mail_template_selector': '_onChangeTemplate',
    },
    /**
     * @constructor
     * @param {Widget} parent
     * @param {int} templateId
     */
    init: function(editor, templateId) {
        this.editor = editor;
        this.templateId = templateId;
        this._super(editor, {
            title: _t('Save Email as'),
            size: "medium",
            buttons: [{
                text: _t("Save"),
                classes: "btn-primary pull-left",
                click: _.bind(this._onSaveButtonClicked, this),
            }, {
                text: _t("Cancel"),
                classes: "pull-left",
                close: true,
            }],
        });
    },

    /*
     * @Override
     */
    start: function() {
        if (!this.editor.templateData.length) {
            this.$('.o_mail_template_name_input').removeClass('hidden');
        }
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * function for onchange radio button for create new template and replace existing template.
     * @private
     */
    _onChangeDialogRadioOptions: function() {
        this.$el.find('.o_mail_template_name_input, .o_mail_template_selector_dropdown').toggleClass('hidden').removeClass('has-error');
    },

    /**
     * function to change template image for selected saved template.
     * @private
     * @param {Event} ev
     */
    _onChangeTemplate: function(e) {
        var templateId = parseInt($(e.currentTarget).val());
        this.templateId = templateId;
        var selectedCustomTemplate = this.editor.getSavedTemplate(templateId);
        this.$el.find('.o_mail_selected_image_area img').attr("src", "data:image/*;base64," + selectedCustomTemplate.image);
    },

    /**
     * function used to Create or Update Email Template using Save Template Dialog's Save Button click.
     * @private
     */
    _onSaveButtonClicked: function() {
        var self = this;
        var name = this.$('input[type=text][name=template_name]').val();
        var $bodyHtml = $editable_area.html();
        if (this.$('input[type=radio][name=template_option_radio][id=replace_existing_tmpl]').is(':checked')) {
            this.$footer.find('.btn-primary').html("<i class='fa fa-spinner fa-spin'/> Save");
            html2canvas($editable_area, {
                onrendered: function(canvas) {
                    var dataURL = canvas.toDataURL('image/png', 0.9).split(',')[1];
                    var args = [
                        [self.templateId], {
                            'body_html': $bodyHtml,
                            'image': dataURL,
                        }
                    ];
                    self.editor.queryTemplate('write', args).then(function() {
                        var selectedCustomTemplate = self.editor.getSavedTemplate(parseInt(self.templateId));
                        selectedCustomTemplate.image = dataURL;
                        self.close();
                    });
                },
                height: 700,
            });
        } else {
            if (name.trim() == "") {
                this.$('.o_mail_template_name_input').addClass('has-error');
            } else {
                this.$footer.find('.btn-primary').html("<i class='fa fa-spinner fa-spin'/> Save");
                html2canvas($editable_area, {
                    onrendered: function(canvas) {
                        var dataURL = canvas.toDataURL('image/png', 0.9).split(',')[1];
                        var args = [{
                            'name': name,
                            'model': 'mail.mass_mailing',
                            'body_html': $bodyHtml,
                            'image': dataURL
                        }];
                        self.editor.queryTemplate('create', args).then(function(id) {
                            var newTemplate = {
                                'name': name,
                                'id': id,
                                'body_html': $bodyHtml,
                                'image': dataURL
                            };
                            self.editor.templateData.push(newTemplate);
                            self.close();
                        });
                    },
                    height: 700,
                });
            }
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

    if (value !==_val) {
        if (editor_enable) {
            if (value !== fields_values[field_name]) {
                rte.history.recordUndo($editable);
            }
            core.bus.trigger('deactivate_snippet');
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

    if (fields_values.mailing_model && editor_enable) {
        if (value.indexOf('on_change_model_and_list') !== -1) {
            odoo_top[callback+"_downup"](_val);
        }
    }
};

if ($editable_area.html().indexOf('on_change_model_and_list') !== -1) {
    $editable_area.empty();
}
});
