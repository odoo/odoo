/** @odoo-module **/

import {PageDependencies} from '@website/components/dialog/page_properties';
import {standardFieldProps} from '@web/views/fields/standard_field_props';
import {useInputField} from '@web/views/fields/input_field_hook';
import {useService} from '@web/core/utils/hooks';
import {Switch} from '@website/components/switch/switch';
import {registry} from '@web/core/registry';

const {Component, useState} = owl;

/**
 * Displays website page dependencies and URL redirect options when the page URL
 * is updated.
 */
class PageUrlField extends Component {
    setup() {
        this.orm = useService('orm');
        this.serverUrl = `${window.location.origin}/`;
        this.pageUrl = this.fieldURL;

        this.state = useState({
            redirect_old_url: false,
            url: this.pageUrl,
            redirect_type: '301',
        });

        useInputField({getValue: () => this.fieldURL});
    }

    get enableRedirect() {
        return this.state.url !== this.pageUrl;
    }

    onChangeRedirectOldUrl(value) {
        this.state.redirect_old_url = value;
        this.updateValues();
    }

    get fieldURL() {
        const value = this.props.value;
        return (value.url !== undefined ? value.url : value).replace(/^\//g, '');
    }

    updateValues() {
        // HACK: update redirect data from the URL field.
        // TODO: remove this and use a transient model with redirect fields.
        this.props.update(this.state);
    }
}
PageUrlField.components = {Switch, PageDependencies};
PageUrlField.template = 'website.PageUrlField';
PageUrlField.props = {
    ...standardFieldProps,
    placeholder: {type: String, optional: true},
};
PageUrlField.extractProps = ({attrs}) => {
    return {
        placeholder: attrs.placeholder,
    };
};
PageUrlField.supportedTypes = ['char'];

registry.category("fields").add("page_url", PageUrlField);

/**
 * Displays 'Selection' field's values as images to select.
 * Image src for each value can be added using the option 'images' on field XML.
 */
export class ImageRadioField extends Component {
    setup() {
        const selection = this.props.record.fields[this.props.name].selection;
        // Check if value / label exists for each selection item and add the
        // corresponding image from field options.
        this.values = selection.filter(item => {
            return item[0] || item[1];
        }).map((value, index) => {
            return [...value, this.props.images && this.props.images[index] || ''];
        });
    }

    /**
     * @param {String} value
     */
    onSelectValue(value) {
        this.props.update(value);
    }
}
ImageRadioField.supportedTypes = ['selection'];
ImageRadioField.template = 'website.FieldImageRadio';
ImageRadioField.props = {
    ...standardFieldProps,
    images: {type: Array, element: String},
};
ImageRadioField.extractProps = ({attrs}) => {
    return {
        images: attrs.options.images,
    };
};

registry.category("fields").add("image_radio", ImageRadioField);
