/** @odoo-module **/

import { _t } from '@web/core/l10n/translation';
import FormEditorRegistry from '@website/js/form_editor_registry';
import { WebsiteFormEditor } from '@website/snippets/s_website_form/options';
import options from '@web_editor/js/editor/snippets.options';
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import "@website/js/editor/snippets.options";

const FormProjectEditor = WebsiteFormEditor.include({
    /**
     * Error dialog that allows the user to be redirected to a another odoo webpage through a window action
     *
     * @param {String} msg the message displayed in the error dialog
     * @param {String} button_txt the text displayed on the dialog's primary button
     * @param {String} redirectAction the window action to redirect user to a view
     * @returns {Promise}
     *
     */
    ErrorWithRedirect: function (msg, button_txt, redirectAction) {
        return new Promise((resolve, reject) => {
            this.dialog.add(ConfirmationDialog, {
                body: msg,
                confirm: async () => {
                    await this._redirectToAction(redirectAction);
                    resolve();
                },
                cancel: () => resolve(),
                confirmLabel: _t(button_txt),
            });
        });
    },

    /**
     * Returns a promise which is resolved once the records of the field
     * have been retrieved.
     *
     * @private
     * @override
     * @param {Object} field
     * @returns {Promise<Object>}
     */
    _fetchFieldRecords: async function (field) {
        // check whether we are looking for the project_id field
        if (field.name !== "project_id") {
            return this._super.apply(this, arguments);
        } else if (field.relation && field.relation !== 'ir.attachment') {
            field.records = await this.orm.call(
                field.relation,
                'search_read',
                [field.domain, ['display_name']],
            );
        }
        return field.records;
    },

    /**
     * Here we edit the way that the form is being rendered.
     * The initial if statement ensures that this code only applies on the "create a task" option of the form.
     * If the "create a task" option is not chosen, the execution is moved to the parent method.
     *
     * It is necessary to do this because an error is raised when the form is edited and no project have been
     * set up. This can only occur when the user has deleted/archived all projects after editing the form
     * @override
     */
    _renderCustomXML: async function (uiFragment) {
        if (this.modelCantChange) {
            return;
        }

        // get the information currently on the form
        const formKey = this.activeForm.website_form_key;
        const formInfo = FormEditorRegistry.get(formKey);

        if (formKey == "create_task") {
            // Add Action select
            const firstOption = uiFragment.childNodes[0];
            uiFragment.insertBefore(this.selectActionEl.cloneNode(true), firstOption);

            if (!formInfo || !formInfo.fields) {
                return;
            }
            const proms = formInfo.fields.map(field => this._fetchFieldRecords(field));
            return Promise.all(proms).then(() => {
                formInfo.fields.forEach(field => {
                    let option;
                    switch (field.type) {
                        case 'many2one':
                            option = this._buildSelect(field);
                            break;
                        case 'char':
                            option = this._buildInput(field);
                            break;
                    }
                    if (field.required) {
                        // We check if the field is required if yes,
                        // check whether the field is many2one with no records and if not,
                        // get default value or for many2one fields the first option.
                        if (!(field.type == 'many2one' && field.records.length == 0)) {
                            const currentValue = this.$target.find(`.s_website_form_dnone input[name="${field.name}"]`).val();
                            const defaultValue = field.defaultValue || field.records[0].id;
                            this._addHiddenField(currentValue || defaultValue, field.name);
                        }
                    }
                    uiFragment.insertBefore(option, firstOption);
                });
            });
        } else {
            return this._super.apply(this, arguments);
        }
    },

    /**
     * @override
     * @param {String} value the id of the model we want the form to adopt
     * Select the model to create with the form.
     * If the model's website_form_key is "create_task" we check whether its project_id
     * field is empty and if yes, raise a warning.
     */
    selectAction: async function (previewMode, value, params) {
        if (this.modelCantChange) {
            return;
        }
        // This operation is done to check which action coresponds
        // to the numeric "value" parameter
        let nextKey;
        this.models.forEach(model => {
            if (String(model.id) == value) {
                nextKey = model.website_form_key;
            }
        })

        if (nextKey == 'create_task') {
            const formInfo = FormEditorRegistry.get(nextKey);
            const proms = formInfo.fields.map(field => this._fetchFieldRecords(field));
            let error;

            await Promise.all(proms).then(() => {
                formInfo.fields.forEach(field => {
                    // Check whether the field is the project_id field
                    // and whether there are any records - if not the warning will be raised
                    if (field.name == 'project_id' && field.records.length == 0) {
                        const msg = "You need to have set-up a project in order to select the option to create a task from \
                                    the website form";
                        const buttonTxt = "Create Project";
                        const action = 'website_form_project.create_project_web_form';

                        error = this.ErrorWithRedirect(msg, buttonTxt, action);
                    }
                });
            });

            if (error) {
                return error;
            } else {
                await this._applyFormModel(parseInt(value));
                this.rerender = true;
            }
        } else {
            this._super.apply(this, arguments);
        }
    },
});

options.registry.form_project_editor = FormProjectEditor;

export default FormProjectEditor;
