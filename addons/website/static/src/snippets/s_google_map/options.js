odoo.define('options.s_google_map_options', function (require) {
'use strict';

const {Dialog} = require('web_editor.widget');
const {_t, qweb} = require('web.core');
const options = require('web_editor.snippets.options');
const {googleScriptLoaded} = require('website.s_google_map');

options.registry.GoogleMap = options.Class.extend({
    xmlDependencies: ['/website/static/src/xml/s_google_map_modal.xml'],
    defaultLocation: '(50.854975,4.3753899)',

    /**
     * @override
     */
    onBuilt() {
        this._super(...arguments);

        let widget = null;
        this.trigger_up('user_value_widget_request', {
            name: 'map_options_opt',
            onSuccess: _widget => widget = _widget,
        });
        widget.$el.click();
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Opens the customization dialog.
     *
     * @see this.selectClass for parameters
     */
    async map(previewMode, widgetValue, params) {
        await new Promise(resolve => {
            this.dialog = new Dialog(this, {
                size: 'medium',
                title: _t("Customize your map"),
                buttons: [
                    {text: _t("Save"), classes: 'btn-primary', close: true, click: () => {
                        if (!this.dialog.$('#placeBk').val()) {
                            this.dialog.$('#placeBk').val(this.defaultLocation);
                        }
                        this.$target[0].dataset.mapGps = this.dialog.$('#placeBk').val();
                        this.$target[0].dataset.pinStyle = this.dialog.$('#pin_style').val();
                        this.$target[0].dataset.pinAddress = this.dialog.$('#pin_address').val();
                    }},
                    {text: _t("Cancel"), close: true}
                ],
                $content: $(qweb.render('website.s_google_map_modal'))
            });

            this.dialog.opened().then(() => {
                this.dialog.$('#pin_address').val(this.$target[0].dataset.pinAddress);
                this.dialog.$('#pin_style').val(this.$target[0].dataset.pinStyle);
                this.dialog.$('#placeBk').val(this.$target[0].dataset.mapGps);
                const autocomplete = new google.maps.places.Autocomplete(this.dialog.$('#pin_address').get(0), {types: ['geocode']});
                google.maps.event.addListener(autocomplete, 'place_changed', () => {
                    const place = autocomplete.getPlace();
                    this.dialog.$('#placeBk').val(place.geometry ? place.geometry.location : this.defaultLocation);
                });
            });

            this.dialog.on('closed', this, () => resolve());

            googleScriptLoaded.then(() => this.dialog.open());
        });
    },
    /**
     * @see this.selectClass for parameters
     */
    resetMapColor(previewMode, widgetValue, params) {
        this.$target[0].dataset.mapColor = '';
    },
});
});
