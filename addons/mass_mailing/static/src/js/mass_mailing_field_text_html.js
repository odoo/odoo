odoo.define('mass_mailing.field_text_html', function (require) {

var FieldTextHtml = require('web_editor.backend').FieldTextHtml;
var fieldRegistry = require('web.field_registry');

var MassMailingFieldTextHtml = FieldTextHtml.extend({
    /**
     * The html_frame widget is opened in an iFrame that has its URL encoded
     * with all the key/values returned by this method.
     *
     * Some fields can get very long values and we want to omit them for the URL building
     *
     * @override
     */
    getDatarecord: function () {
        return _.omit(this._super(), [
            'mailing_domain',
            'contact_list_ids',
            'body_html',
            'attachment_ids'
        ]);
    }
});

fieldRegistry.add('mass_mailing_html_frame', MassMailingFieldTextHtml);

return MassMailingFieldTextHtml;

});
