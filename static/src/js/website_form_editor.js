odoo.define('website_form_editor', function (require) {
    'use strict';

    /**
     * @todo this should be entirely refactored
     */

    var core = require('web.core');
    var options = require('web_editor.snippets.options');
    var wUtils = require('website.utils');

    var qweb = core.qweb;

    options.registry['website_form_editor'] = options.Class.extend({
        xmlDependencies: ['/website_form_editor/static/src/xml/website_form_editor.xml'],

        // Generic modal code
        build_modal: function (modal_title, modal_body, on_save) {
            var self = this;

            // Build the form parameters modal
            var modal = qweb.render("website_form_editor.modal", {
                modal_title: modal_title,
                modal_body: modal_body
            });

            self.$modal = $(modal);
            self.$modal.appendTo('body');

            // Process the modal on_save then hide it
            self.$modal.find("#modal-save").on('click', function (e){
                if (self.$modal.find("form")[0].checkValidity()) {
                    on_save();
                    self.$modal.modal('hide');
                } else {
                    _.each(self.$modal.find('input'), function (input) {
                        var $field = $(input).closest('.form-field');
                        $field.removeClass('o_has_error').find('.form-control, .custom-select').removeClass('is-invalid');
                        if (!input.checkValidity()) {
                            $field.addClass('o_has_error').find('.form-control, .custom-select').addClass('is-invalid');
                        }
                    });
                }
            });

            // Destroy the modal when it is closed, as we will use many of them
            self.$modal.on('hidden.bs.modal', function (e) {
              self.$modal.remove();
          });

            self.$modal.modal();

            return self.$modal;
        },

        // Return the fields deferred if we already issued a model
        // fields fetch request, or issue said request.
        fields: function () {
            return this.fields_deferred || this.fetch_model_fields();
        },

        fetch_model_fields: function () {
            var self = this;
            this.fields_deferred = new $.Deferred();
            this._rpc({
                model: "ir.model",
                method: "get_authorized_fields",
                args: [this.$target.closest('form').attr('data-model_name')],
            }).then(function (fields) {
                // The get_fields function doesn't return the name
                // in the field dict since it uses it has the key
                _.map(fields, function (field, field_name){
                    field.name = field_name;
                    return field;
                });

                self.fields_deferred.resolve(fields);
            });
            return this.fields_deferred;
        },

        // Choose a model modal
        website_form_model_modal: function (previewMode, value, $li) {
            var self = this;
            this._rpc({
                model: "ir.model",
                method: "search_read",
                args: [
                    [['website_form_access', '=', true]],
                    ['id', 'model', 'name', 'website_form_label']
                ],
            }).then(function (models) {
                // Models selection input
                var model_selection = qweb.render("website_form_editor.field_many2one", {
                    field: {
                        name: 'model_selection',
                        string: 'Action',
                        records: _.map(models, function (m) {
                            return {
                                id: m.model,
                                display_name: m.website_form_label || m.name,
                                selected: (m.model === self.$target.attr('data-model_name')) ? 1 : null,
                            };
                        }),
                    }
                });

                // Success page input
                var success_page = qweb.render("website_form_editor.field_char", {
                    field: {
                        name: 'success_page',
                        string: 'Thank You Page',
                        value: self.$target.attr('data-success_page')
                    }
                });

                // Form parameters modal
                self.build_modal(
                    "Form Parameters",
                    model_selection + success_page,
                    function () {
                        var model_name = self.$modal.find("[name='model_selection']").val();
                        var success_page = self.$modal.find("[name='success_page']").val();
                        self.init_form(model_name);
                        self.$target.attr('data-success_page', success_page);

                        // Add magic email_to input if model is mail.mail
                        self.$target.find("input.form-field[name='email_to']").remove();
                        if (model_name === 'mail.mail') {
                            var email_to = self.$modal.find("input[name='email_to']").val();
                            self.$target.append("<input class='form-field' type='hidden' name='email_to' value=" + email_to + ">");
                        }
                    }
                );

                self.$modal.find("label.col-form-label[for='success_page']").css('font-weight', 'normal');
                wUtils.autocompleteWithPages(self, self.$modal.find("input[name='success_page']"));
                self.toggle_email_to();

                self.$modal.find("[name='model_selection']").on('change', function () {
                    self.toggle_email_to();
                });

                // On modal close, if there is no data-model, it means
                // that the user refused to configure the form on the
                // first modal, so we remove the snippet.
                self.$modal.on('hidden.bs.modal', function (e) {
                    if (!self.$target.attr('data-model_name')){
                        self.$target.remove();
                    }
                });
            });
        },

        // Choose a field modal
        website_form_field_modal: function (previewMode, value, $li) {
            var self = this;

            this.fields().then(function (fields) {
                // Make a nice array to render the select input
                var fields_array = _.map(fields, function (v, k) { return {id: k, name: v.name, display_name: v.string}; });
                // Filter the fields to remove the ones already in the form
                var fields_in_form = _.map(self.$target.find('.col-form-label'), function (label) { return label.getAttribute('for'); });
                var available_fields = _.filter(fields_array, function (field) { return !_.contains(fields_in_form, field.name); });
                // Render the select input
                var field_selection = qweb.render("website_form_editor.field_many2one", {
                    field: {
                        name: 'field_selection',
                        string: 'Field',
                        records: _.sortBy(available_fields, 'display_name')
                    }
                });

                // Form parameters modal
                self.build_modal(
                    "Field Parameters",
                    field_selection,
                    function () {
                        var selected_field_name = self.$modal.find("[name='field_selection']").val();
                        var selected_field = fields[selected_field_name];
                        self.append_field(selected_field);
                    }
                );
            });
        },

        // Create a custom field
        website_form_custom_field: function (previewMode, value, $li) {
            var default_field_name = 'Custom ' + $li.text();
            this.append_field({
                name: default_field_name,
                string: default_field_name,
                custom: true,
                type: value,
                // Default values for x2many fields
                records: [
                    {
                        id: 'Option 1',
                        display_name: 'Option 1'
                    },
                    {
                        id: 'Option 2',
                        display_name: 'Option 2'
                    },
                    {
                        id: 'Option 3',
                        display_name: 'Option 3'
                    }
                ],
                // Default values for selection fields
                selection: [
                    [
                        'Option 1',
                        'Option 1'
                    ],
                    [
                        'Option 2',
                        'Option 2'
                    ],
                    [
                        'Option 3',
                        'Option 3'
                    ],
                ]
            });
        },

        // Re-render the field and replace the current one
        // website_form_editor_field_reset: function(previewMode, value, $li) {
        //     var self = this;
        //     var target_field_name = this.$target.find('.col-form-label').attr('for');
        //     this.fields().then(function(fields){
        //         self.render_field(fields[target_field_name]).done(function(field){
        //             self.$target.replaceWith(field);
        //         })
        //     });
        // },

        toggle_email_to: function () {
            // Display or remove the magic email_to field for model mail.mail
            var selected_model_name = this.$modal.find("[name='model_selection']").val();
            var $current = this.$modal.find(".form-field:has(input[name='email_to'])");
            if (selected_model_name !== 'mail.mail') {
                $current.remove();
            } else if (!$current.length) { // only add field if it's not already here
                this.$modal.find("form").append(
                    // Email To input
                    $(qweb.render("website_form_editor.field_char", {
                        field: {
                            name: 'email_to',
                            string: 'Recipient email',
                            required: true,
                            value: this.$target.find("input[name='email_to']").val()
                        }
                    }))
                );
            }
        },

        append_field: function (field) {
            var self = this;
            this.render_field(field).done(function (field){
                self.$target.find(".form-group:has('.o_website_form_send')").before(field);
            });
        },

        render_field: function (field) {
            var field_rendered = $.Deferred();

            // Convert the required boolean to a value directly usable
            // in qweb js to avoid duplicating this in the templates
            field.required = field.required ? 1 : null;

            // Fetch possible values for relation fields
            var fetch_field_relation = $.Deferred();
            if (field.relation && field.relation !== 'ir.attachment') {
                this._rpc({
                    model: field.relation,
                    method: 'search_read',
                    args: [
                        field.domain || [],
                        ['display_name']
                    ],
                }).then(function (records) {
                    field.records = records;
                    fetch_field_relation.resolve();
                });
            }
            else {
                fetch_field_relation.resolve();
            }

            fetch_field_relation.done(function () {
                field_rendered.resolve(
                    qweb.render("website_form_editor.field_" + field.type, {field: field})
                );
            });

            return field_rendered;
        },

        onBuilt: function () {
            // Open the parameters modal on snippet drop
            this.website_form_model_modal('click', null, null);
        },

        init_form: function (model_name) {
            var self = this;
            if (model_name !== this.$target.attr('data-model_name')) {
                // Reset the form
                this.$target.attr('data-model_name', model_name);
                this.$target.find(".form-field:not(:has('.o_website_form_send'))").remove();

                // Force fetch the fields of the new model
                // and render all model required fields
                this.fetch_model_fields().then(function (fields) {
                    _.each(fields, function (field, field_name){
                        if (field.required) {
                            self.append_field(field);
                        }
                    });
                });
            }
        },

        cleanForSave: function () {
            var model = this.$target.data('model_name');
            // because apparently this can be called on the wrong widget and
            // we may not have a model, or fields...
            if (model) {
                // we may be re-whitelisting already whitelisted fields. Doesn't
                // really matter.
                var fields = this.$target.find('input.form-field[name=email_to], .form-field:not(.o_website_form_custom) :input').map(function (_, node) {
                    return node.getAttribute('name');
                }).get();
                if (fields.length) {
                    // ideally we'd only do this if saving the form
                    // succeeds... but no idea how to do that
                    this._rpc({
                        model: 'ir.model.fields',
                        method: 'formbuilder_whitelist',
                        args: [model, _.uniq(fields)],
                    });
                }
            }

            // Prevent saving of the error colors  // TODO: would be better on Edit
            this.$target.find('.o_has_error').removeClass('o_has_error').find('.form-control, .custom-select').removeClass('is-invalid');

            // Prevent saving of the status message  // TODO: would be better on Edit
            this.$target.find('#o_website_form_result').empty();

            // Update values of custom inputs to mirror their labels
            var custom_inputs = this.$target.find('.o_website_form_custom .o_website_form_input');
            _.each(custom_inputs, function (input, index) {
                // Change the custom field name according to their label
                var field_label = $(input).closest('.form-field').find('label:first');
                input.name = field_label.text().trim();
                field_label.attr('for', input.name);

                // Change the custom radio or checkboxes values according to their label
                if (input.type === 'radio' || input.type === 'checkbox') {
                    var checkbox_label = $(input).closest('label').text().trim();
                    if (checkbox_label) {
                        input.value = checkbox_label;
                    }
                }
            });
        }
    });

    // Generic custom field options
    options.registry['website_form_editor_field'] = options.Class.extend({
        xmlDependencies: ['/website_form_editor/static/src/xml/website_form_editor.xml'],

        // Option to toggle inputs required attribute
        website_form_field_require: function (previewMode, value, $li) {
            this.$target.find('.o_website_form_input').each(function (index, input) {
                input.required = !input.required;
            });
        }
    });

    // Dirty hack to transform select fields into an editable construct
    options.registry['website_form_editor_field_select'] = options.Class.extend({
        xmlDependencies: ['/website_form_editor/static/src/xml/website_form_editor.xml'],

        start: function () {
            if (!this.$target.find('#editable_select').length) {
                var self = this;
                var select = this.$target.find('select');
                select.hide();
                this.editable_select = $('<div id="editable_select" class="form-control o_website_form_input"/>');
                _.each(select.children(), function (option) {
                    self.editable_select.append(
                        $('<div id="' + $(option).attr('value') + '" class="o_website_form_select_item">' + $(option).text().trim() + '</div>')
                    );
                });
                select.after(this.editable_select);
            }
        },

        cleanForSave: function () {
            if (this.$target.find('#editable_select').length) {
                var self = this;
                // Reconstruct the field from the select tag
                var select = this.$target.find('select');
                var field = {
                    name: select.attr('name'),
                    string: this.$target.find('.col-form-label').text().trim(),
                    required: self.$target.hasClass('o_website_form_required'),
                    custom: self.$target.hasClass('o_website_form_custom'),
                };

                // Build the new records list from the editable select field
                var records = [];
                var editable_options = this.$target.find('#editable_select .o_website_form_select_item');
                _.each(editable_options, function (option) {
                    records.push({
                        id: self.$target.hasClass('o_website_form_custom') ? $(option).text().trim() : $(option).attr('id'),
                        display_name: $(option).text().trim()
                    });
                });
                field.records = records;

                // Replace this field by the new one
                var $new_select = $(qweb.render("website_form_editor.field_many2one", {field: field}));
                // Reapply the custom style classes
                if (this.$target.hasClass('o_website_form_required_custom')) {
                    $new_select.addClass('o_website_form_required_custom');
                }
                if (this.$target.hasClass('o_website_form_field_hidden')) {
                    $new_select.addClass('o_website_form_field_hidden');
                }
                this.$target.replaceWith($new_select);
            }
        }
    });

    // Superclass for options that need to disable a button from the snippet overlay
    var disable_overlay_button_option = options.Class.extend({
        xmlDependencies: ['/website_form_editor/static/src/xml/website_form_editor.xml'],

        // Disable a button of the snippet overlay
        disable_button: function (button_name, message) {
            // TODO refactor in master
            var className = 'oe_snippet_' + button_name;
            this.$overlay.on('click', '.' + className, this.prevent_button);
            var $button = this.$overlay.find('.' + className);
            $button.attr('title', message).tooltip({delay: 0});
            $button.removeClass(className); // Disable the functionnality
        },

        prevent_button: function (event) {
            // Snippet options bind their functions before the editor, so we
            // can't cleanly unbind the editor onRemove function from here
            event.preventDefault();
            event.stopImmediatePropagation();
        }
    });

    // Disable duplicate button for model fields
    options.registry['website_form_editor_field_model'] = disable_overlay_button_option.extend({
        start: function () {
            this.disable_button('clone', 'You can\'t duplicate a model field.');
        }
    });

    // Disable delete button for model required fields
    options.registry['website_form_editor_field_required'] = disable_overlay_button_option.extend({
        start: function () {
            this.disable_button('remove', 'You can\'t remove a field that is required by the model itself.');
        }
    });

    // Disable duplicate button for non-custom checkboxes and radio buttons
    options.registry['website_form_editor_field_x2many'] =disable_overlay_button_option.extend({
        start: function () {
            this.disable_button('clone', 'You can\'t duplicate an item which refers to an actual record.');
        }
    });
});
