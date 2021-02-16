const { Component } = owl;
const { xml } = owl.tags;
const { whenReady } = owl.utils;

// Owl Components
class App extends Component {
    static template = xml`<div id="formio_builder"></div>`;

    willStart() {
        this.loadBuilder();
    }

    loadBuilder() {
        const self = this;
        self.builderId = document.getElementById('builder_id').value;
        self.configUrl = '/formio/builder/' + self.builderId + '/config';
        self.saveUrl = '/formio/builder/' + self.builderId + '/save';
        self.schema = {};
        self.options = {};
        self.params = {};

        $.jsonRpc.request(self.configUrl, 'call', {}).then(function(result) {
            if (!$.isEmptyObject(result)) {
                self.schema = result.schema;
                self.options = result.options;
                self.params = result.params;
                self.createBuilder();
            }
        });
    }

    createBuilder() {
        const self = this;
        const builder = new Formio.FormBuilder(document.getElementById('formio_builder'), self.schema, self.options);

        builder.instance.ready.then(function() {
            if ('language' in self.options) {
                builder.language = self.options['language'];
                // builder.instance.webform.language = self.options['language'];
            }
            window.setLanguage = function(lang) {
                builder.instance.webform.language = lang;
                builder.instance.redraw();
            };
        });

        builder.instance.on('change', function(res) {
            if (! res.hasOwnProperty('components')) {
                return;
            }
            else if ('readOnly' in self.params && self.params['readOnly'] == true) {
                alert("This Form Builder is readonly. It's state is either Current or Obsolete. Refresh the page again.");
                return;
            }
            else {
                console.log('[Forms] Saving Builder...');
                $.jsonRpc.request(self.saveUrl, 'call', {
                    'builder_id': self.builderId,
                    'schema': res
                }).then(function() {
                    console.log('[Forms] Builder sucessfully saved.');
                });
            }
        });
    }
}

// Setup code
function setup() {
    const app = new App();
    app.mount(document.getElementById('formio_builder_app'));
}

whenReady(setup);
