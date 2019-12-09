odoo.define('website_form_editor', function (require) {
    'use strict';

    /**
     * @todo this should be entirely refactored
     */

    var ajax = require('web.ajax');
    var core = require('web.core');
    var Dialog = require('web.Dialog');
    var FormEditorRegistry = require('website_form.form_editor_registry');
    var options = require('web_editor.snippets.options');
    var wUtils = require('website.utils');
    var Wysiwyg = require('web_editor.wysiwyg');

    var qweb = core.qweb;
    var _t = core._t;

    var FormEditorDialog = Dialog.extend({
        /**
         * @constructor
         */
        init: function (parent, options) {
            this._super(parent, _.extend({
                buttons: [{
                    text: _t('Save'),
                    classes: 'btn-primary',
                    close: true,
                    click: this._onSaveModal.bind(this),
                }, {
                    text: _t('Cancel'),
                    close: true
                }],
            }, options));
        },

        //----------------------------------------------------------------------
        // Handlers
        //----------------------------------------------------------------------

        /**
         * @private
         */
        _onSaveModal: function () {
            if (this.$el[0].checkValidity()) {
                this.trigger_up('save');
            } else {
                _.each(this.$el.find('.o_website_form_input'), function (input) {
                    var $field = $(input).closest('.form-field');
                    $field.removeClass('o_has_error').find('.form-control, .custom-select').removeClass('is-invalid');
                    if (!input.checkValidity()) {
                        $field.addClass('o_has_error').find('.form-control, .custom-select').addClass('is-invalid');
                    }
                });
            }
        },
    });

    options.registry['website_form_editor'] = options.Class.extend({
        xmlDependencies: ['/website_form/static/src/xml/website_form_editor.xml'],

        start: function () {
            this.$target.addClass('o_fake_not_editable').attr('contentEditable', false);
            this.$target.find('label:not(:has(span)), label span').addClass('o_fake_editable').attr('contentEditable', true);
            return this._super.apply(this, arguments);
        },

        // Return the fields promise if we already issued a model
        // fields fetch request, or issue said request.
        fields: function () {
            return this.fields_promise || this.fetch_model_fields();
        },

        fetch_model_fields: function () {
            return this._rpc({
                model: "ir.model",
                method: "get_authorized_fields",
                args: [this.$target.closest('form').attr('data-model_name')],
            }).then(function (fields) {
                // The get_fields function doesn't return the name
                // in the field dict since it uses it has the key
                _.each(fields, function (field, field_name) {
                    field.name = field_name;
                });
                return fields;
            });
        },

        // Choose a model modal
        website_form_model_modal: function (previewMode, value, $li) {
            var self = this;
            this._rpc({
                model: "ir.model",
                method: "search_read",
                args: [
                    [['website_form_access', '=', true]],
                    ['id', 'model', 'name', 'website_form_label', 'website_form_key']
                ],
            }).then(function (models) {
                self.models = models;
                // Models selection input
                var modelSelection = qweb.render("website_form.field_many2one", {
                    field: {
                        name: 'model_selection',
                        string: 'Action',
                        required: true,
                        records: _.map(models, function (m) {
                            return {
                                id: m.id,
                                display_name: m.website_form_label || m.name,
                                selected: (m.model === self.$target.attr('data-model_name')) ? 1 : null,
                            };
                        }),
                    }
                });

                // Success page input
                var successPage = qweb.render("website_form.field_char", {
                    field: {
                        name: 'success_page',
                        string: 'Thank You Page',
                        value: self.$target.attr('data-success_page')
                    }
                });

                var save = function () {
                    var successPage = this.$el.find("[name='success_page']").val();
                    self.init_form();
                    self.$target.attr('data-success_page', successPage);

                    this.$el.find('.o_form_parameter_custom').each(function () {
                        var $field = $(this).find('.o_website_form_input');
                        var value = $field.val();
                        var fieldName = $field.attr('name');
                        self.$target.find('.form-group:has("[name=' + fieldName + ']")').remove();
                        if (value) {
                            var $hiddenField = $(qweb.render('website_form.field_char', {
                                field: {
                                    name: fieldName,
                                    value: value,
                                }
                            })).addClass('d-none');
                            self.$target.find('.form-group:has(".o_website_form_send")').before($hiddenField);
                        }
                    });
                };

                var cancel = function () {
                    if (!self.$target.attr('data-model_name')) {
                        self.$target.remove();
                    }
                };

                var $content = $('<form role="form">' + modelSelection + successPage + '</form>');
                var dialog = new FormEditorDialog(self, {
                    title: 'Form Parameters',
                    size: 'medium',
                    $content: $content,
                }).open();
                dialog.on('closed', this, cancel);
                dialog.on('save', this, ev => {
                    ev.stopPropagation();
                    save.call(dialog);
                });

                wUtils.autocompleteWithPages(self, $content.find("input[name='success_page']"));
                self.originSuccessPage = $content.find("input[name='success_page']").val();
                self.originFormID = $content.find("[name='model_selection']").val();
                self._renderParameterFields($content);

                $content.find("[name='model_selection']").on('change', function () {
                    self._renderParameterFields($content);
                });
            });
        },

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        /**
         * @private
         * @returns {Promise}
         */
        _renderParameterFields: function ($modal) {
            var self = this;
            var $successPage = $modal.find("[name='success_page']");
            $modal.find('.o_form_parameter_custom').remove();
            var id = $modal.find("[name='model_selection']").val();
            this.activeForm = _.findWhere(this.models, {id: parseInt(id)});
            var formKey = this.activeForm.website_form_key;
            if (!formKey) {
                return Promise.resolve();
            }
            var proms = [];
            var formInfo = FormEditorRegistry.get(formKey);

            if (this.originFormID === id) {
                $successPage.val(this.originSuccessPage || formInfo.successPage || '/contactus-thank-you');
            } else {
                $successPage.val(formInfo.successPage || '/contactus-thank-you');
            }

            if (formInfo.fields && formInfo.fields.length) {
                _.each(formInfo.fields, function (field) {
                    var value = self.$target.find('[name="' + field.name + '"]').val();
                    proms.push(self.render_field(field).then(function ($field) {
                        $field.addClass('o_form_parameter_custom');
                        // Remove content editable (Added by render_field)
                        $field.find('label').removeAttr('contenteditable');
                        // Set tooltip on label
                        $field.find('label').attr('title', field.title);
                        // Set value
                        $field.find('.o_website_form_input').val(value);
                        $modal.append($field);
                    }));
                });
            }
            return Promise.all(proms);
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
                var fieldSelection = qweb.render("website_form.field_many2one", {
                    field: {
                        name: 'field_selection',
                        string: 'Field',
                        records: _.sortBy(available_fields, 'display_name')
                    }
                });

                var save = function () {
                    var selectedFieldName = this.$el.find("[name='field_selection']").val();
                    var selectedField = fields[selectedFieldName];
                    self.append_field(selectedField);
                };

                var dialog = new FormEditorDialog(self, {
                    title: 'Field Parameters',
                    size: 'medium',
                    $content: '<form role="form">' + fieldSelection + '</form>',
                }).open();
                dialog.on('save', this, ev => {
                    ev.stopPropagation();
                    save.call(dialog);
                });
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

        append_field: function (field) {
            var self = this;
            this.render_field(field).then(function (field){
                self.$target.find(".form-group:has('.o_website_form_send')").before(field);
            });
        },

        render_field: function (field) {
            // Convert the required boolean to a value directly usable
            // in qweb js to avoid duplicating this in the templates
            field.required = field.required ? 1 : null;

            // Fetch possible values for relation fields
            var fieldRelationProm;
            if (field.relation && field.relation !== 'ir.attachment') {
                fieldRelationProm = this._rpc({
                    model: field.relation,
                    method: 'search_read',
                    args: [
                        field.domain || [],
                        ['display_name']
                    ],
                }).then(function (records) {
                    field.records = records;
                });
            }

            return Promise.resolve(fieldRelationProm).then(function () {
                var $content = $(qweb.render("website_form.field_" + field.type, {field: field}));
                $content.find('label:not(:has(span)), label span').addClass('o_fake_editable').attr('contentEditable', true);
                return $content;
            });
        },

        onBuilt: function () {
            // Open the parameters modal on snippet drop
            this.website_form_model_modal('click', null, null);
        },

        /**
         * Hide change form parameters option for forms
         * e.g. User should not be enable to change existing job application form to opportunity form in 'Apply job' page.
         *
         * @override
         */
        onFocus: function () {
            this.$el.filter('[data-website_form_model_modal]').toggleClass('d-none', this.$target.attr('hide-change-model') !== undefined);
        },

        init_form: function () {
            var self = this;
            var modelName = this.activeForm.model;
            var formKey = this.activeForm.website_form_key;
            if (modelName !== this.$target.attr('data-model_name')) {
                this.$target.attr('data-model_name', modelName);
                this.$target.find(".form-field:not(:has('.o_website_form_send')), .o_form_heading").remove();

                if (formKey) {
                    var formInfo = FormEditorRegistry.get(formKey);
                    ajax.loadXML(formInfo.defaultTemplatePath, qweb).then(function () {
                        // Append form title
                        $('<h1>', {
                            class: 'o_form_heading',
                            text: self.activeForm.website_form_label,
                        }).prependTo(self.$target.find('.container'));
                        self.$target.find('.form-group:has(".o_website_form_send")').before($(qweb.render(formInfo.defaultTemplateName)));
                    });
                } else {
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
        xmlDependencies: ['/website_form/static/src/xml/website_form_editor.xml'],

        // Option to toggle inputs required attribute
        website_form_field_require: function (previewMode, value, $li) {
            this.$target.find('.o_website_form_input').each(function (index, input) {
                input.required = !input.required;
            });
        }
    });

    // Dirty hack to transform select fields into an editable construct
    options.registry['website_form_editor_field_select'] = options.Class.extend({
        xmlDependencies: ['/website_form/static/src/xml/website_form_editor.xml'],

        start: function () {
            if (!this.$target.find('#editable_select').length) {
                var self = this;
                var select = this.$target.find('select');
                select.hide();
                this.editable_select = $('<div id="editable_select" class="form-control o_website_form_input" contenteditable="true"/>');
                _.each(select.children(), function (option) {
                    self.editable_select.append(
                        $('<div id="' + $(option).attr('value') + '" class="o_website_form_select_item">' + $(option).text().trim() + '</div>')
                    );
                });
                select.after(this.editable_select);
            }
            return this._super.apply(this, arguments);
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
                var $new_select = $(qweb.render("website_form.field_many2one", {field: field}));
                // Reapply the custom style classes
                if (this.$target.hasClass('o_website_form_required_custom')) {
                    $new_select.addClass('o_website_form_required_custom');
                }
                if (this.$target.hasClass('o_website_form_field_hidden')) {
                    $new_select.addClass('o_website_form_field_hidden');
                }
                var labelClasses = this.$target.find('> div:first').attr('class');
                var inputClasses = this.$target.find('> div:last').attr('class');
                $new_select.find('> div:first').attr('class', labelClasses);
                $new_select.find('> div:last').attr('class', inputClasses);
                this.$target.replaceWith($new_select);
            }
        }
    });

    // allow breaking of form select items, to create new ones
    Wysiwyg.include({
        /**
         * @override
         */
        _editorOptions: function () {
            var options = this._super.apply(this, arguments);
            var isUnbreakableNode = options.isUnbreakableNode;
            options.isUnbreakableNode = function (node) {
                var isSelItem = $(node).hasClass('o_website_form_select_item');
                return isUnbreakableNode(node) && !isSelItem;
            };
            return options;
        },
    });

    // Superclass for options that need to disable a button from the snippet overlay
    var disable_overlay_button_option = options.Class.extend({
        xmlDependencies: ['/website_form/static/src/xml/website_form_editor.xml'],

        // Disable a button of the snippet overlay
        disable_button: function (button_name, message) {
            // TODO refactor in master
            var className = 'oe_snippet_' + button_name;
            this.$overlay.add(this.$overlay.data('$optionsSection')).on('click', '.' + className, this.prevent_button);
            var $button = this.$overlay.add(this.$overlay.data('$optionsSection')).find('.' + className);
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
            return this._super.apply(this, arguments);
        }
    });

    // Disable delete button for model required fields
    options.registry['website_form_editor_field_required'] = disable_overlay_button_option.extend({
        start: function () {
            this.disable_button('remove', 'You can\'t remove a field that is required by the model itself.');
            return this._super.apply(this, arguments);
        }
    });

    // Disable duplicate button for non-custom checkboxes and radio buttons
    options.registry['website_form_editor_field_x2many'] =disable_overlay_button_option.extend({
        start: function () {
            this.disable_button('clone', 'You can\'t duplicate an item which refers to an actual record.');
            return this._super.apply(this, arguments);
        }
    });
});
