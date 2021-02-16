// Copyright Nova Code (http://www.novacode.nl)
// See LICENSE file for full licensing details.

const { Component } = owl;
const { xml } = owl.tags;
const { whenReady } = owl.utils;
const { useState } = owl.hooks;

const actions = {};

const initialState = {
    auth: [],
};

export class OdooFormioForm extends Component {

    constructor(parent, props) {
        super(parent, props);

        this.schema = {};
        this.options = {};
        this.params = {}; // extra params from Odoo backend

        this.baseUrl = window.location.protocol + '//' + window.location.host;
        this.urlParams = new URLSearchParams(window.location.search);

        // by initForm
        this.builderUuid = null;
        this.formUuid = null;
        this.configUrl = null;
        this.submissionUrl = null;
        this.submitUrl = null;
    }

    willStart() {
        this.initForm();
    }

    mounted() {
        this.loadForm();
    }

    initForm() {
        // Implemented in specific (*_app.js) classes.
    }

    submitDone(submission) {
        // Implemented in specific (*_app.js) classes.
    }

    loadForm() {
        const self = this;

        $.jsonRpc.request(self.configUrl, 'call', {}).then(function(result) {
            if (!$.isEmptyObject(result)) {
                self.schema = result.schema;
                self.options = result.options;
                self.params = result.params;
                self.createForm();
            }
        });
    }

    createForm() {
        const self = this;

        // Maybe avoid URL (check) on self.formUuid
        if (self.formUuid) {
            const hooks = {
                'addComponent': function(component, comp, parent) {
                    if (component.hasOwnProperty('data') &&
                        component.data.hasOwnProperty('url') && !$.isEmptyObject(component.data.url)) {
                        component.data.url = self.baseUrl.concat('/formio/form/',  self.formUuid, component.data.url);
                    }
                    return component;
                }
            };
            self.options['hooks'] = hooks;
        }
        Formio.setBaseUrl(window.location.href);
        Formio.createForm(document.getElementById('formio_form'), self.schema, self.options).then(function(form) {
            // Language
            if ('language' in self.options) {
                form.language = self.options['language'];
            }
            window.setLanguage = function(lang) {
                form.language = lang;
            };

            // Events
            form.on('submit', function(submission) {
                const data = {'data': submission.data};
                if (self.formUuid) {
                    data['form_uuid'] = self.formUuid;
                }
                $.jsonRpc.request(self.submitUrl, 'call', data).then(function() {
                    form.emit('submitDone', submission);
                });
            });
            form.on('submitDone', function(submission) {
                self.submitDone(submission);
            });

            // Set the Submission (data)
            // https://github.com/formio/formio.js/wiki/Form-Renderer#setting-the-submission
            if (self.submissionUrl) {
                $.jsonRpc.request(self.submissionUrl, 'call', {}).then(function(result) {
                    if (!$.isEmptyObject(result)) {
                    form.submission = {'data': JSON.parse(result)};
                    }
                });
            }
        });
    }
}
