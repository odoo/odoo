odoo.define('website.settings', function (require) {

const core = require('web.core');
const Dialog = require('web.Dialog');
const FieldBoolean = require('web.basic_fields').FieldBoolean;
const fieldRegistry = require('web.field_registry');

const QWeb = core.qweb;
const _t = core._t;

const WebsiteCookiesbarField = FieldBoolean.extend({
    xmlDependencies: ['/website/static/src/xml/website.res_config_settings.xml'],

    _onChange: function () {
        const checked = this.$input[0].checked;
        if (!checked) {
            return this._setValue(checked);
        }

        const cancelCallback = () => this.$input[0].checked = !checked;
        Dialog.confirm(this, null, {
            title: _t("Please confirm"),
            $content: QWeb.render('website.res_config_settings.cookies_modal_main'),
            buttons: [{
                text: _t('Do not activate'),
                classes: 'btn-primary',
                close: true,
                click: cancelCallback,
            },
            {
                text: _t('Activate anyway'),
                close: true,
                click: () => this._setValue(checked),
            }],
            cancel_callback: cancelCallback,
        });
    },
});

fieldRegistry.add('website_cookiesbar_field', WebsiteCookiesbarField);
});
