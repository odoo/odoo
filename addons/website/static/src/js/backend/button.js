odoo.define('website.backend.button', function (require) {
'use strict';

const AbstractFieldOwl = require('web.AbstractFieldOwl');
const fieldRegistry = require('web.field_registry_owl');

class WebsitePublishButtonOWL extends AbstractFieldOwl {
    /**
     * A boolean field is always set since false is a valid value.
     *
     * @override
     */
    get isSet() {
        return true;
    }

}

WebsitePublishButtonOWL.supportedFieldTypes = ['boolean'];
WebsitePublishButtonOWL.template = 'WidgetWebsitePublishButton';

class WidgetWebsiteButtonIconOWL extends AbstractFieldOwl {
    /**
     * return information whether published/unpublished
     *
     * @returns {string}
     */
    get info() {
        return this.value ? this.env._t('Published') : this.env._t('Unpublished')
    }
    /**
     * @override
     */
    get isSet() {
        return true;
    }
    /**
     * Redirects to the website page of the record.
     *
     * @private
     */
    _onClick() {
        this.trigger('button_clicked', {
            attrs: {
                type: 'object',
                name: 'open_website_url',
            },
            record: this.record,
        });
    }
}

WidgetWebsiteButtonIconOWL.template = 'WidgetWebsiteButtonIcon';

fieldRegistry
    .add('website_redirect_button', WidgetWebsiteButtonIconOWL)
    .add('website_publish_button', WebsitePublishButtonOWL);
});
