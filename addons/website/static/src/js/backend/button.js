odoo.define('website.backend.button', function (require) {
'use strict';

const AbstractFieldOwl = require('web.AbstractFieldOwl');
const field_registry_owl = require('web.field_registry_owl');

class WebsitePublishButtonOWL extends AbstractFieldOwl {
    /**
     * A boolean field is always set since false is a valid value.
     *
     * @override
     */
    isSet() {
        return true;
    }
}

WebsitePublishButtonOWL.supportedFieldTypes = ['boolean'];
WebsitePublishButtonOWL.template = 'WidgetWebsitePublishButton';

class WidgetWebsiteButtonIconOWL extends AbstractFieldOwl {
    /**
     * @override
     */
    isSet() {
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

field_registry_owl
    .add('website_redirect_button', WidgetWebsiteButtonIconOWL)
    .add('website_publish_button', WebsitePublishButtonOWL);
});
