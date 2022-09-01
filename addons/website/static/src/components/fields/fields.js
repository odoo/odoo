/** @odoo-module **/

import {PageDependencies} from '@website/components/dialog/page_properties';
import {standardFieldProps} from '@web/views/fields/standard_field_props';
import {useInputField} from '@web/views/fields/input_field_hook';
import {useService} from '@web/core/utils/hooks';
import {Switch} from '@website/components/switch/switch';
import {registry} from '@web/core/registry';
import {formatChar} from '@web/views/fields/formatters';

const {Component, useState, onWillStart} = owl;

/**
 * Displays website page dependencies and URL redirect options when the page URL
 * is updated.
 */
class PageUrlField extends Component {
    setup() {
        this.state = useState({
            redirect_old_url: false,
            url: this.props.value,
            redirect_type: '301',
        });
        useInputField({getValue: () => this.props.value.url || this.props.value});

        this.serverUrl = window.location.origin;
        this.pageUrl = this.props.value;
    }

    get enableRedirect() {
        return this.state.url !== this.pageUrl;
    }

    onChangeRedirectOldUrl(value) {
        this.state.redirect_old_url = value;
        this.updateValues();
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
 * Used to display key dependencies and warn user about changing a special file
 * (website.page & supported mimetype) name, since the key will be updated too.
 */
class PageNameField extends Component {
    setup() {
        this.orm = useService('orm');

        useInputField({getValue: () => this.props.value || ''});
        this.state = useState({
            name: this.props.value,
        });

        this.pageName = this.props.value;
        this.supportedMimetypes = {};

        onWillStart(() => this.onWillStart());
    }

    get formattedPageName() {
        return formatChar(this.props.value);
    }

    async onWillStart() {
        this.supportedMimetypes = await this.orm.call('website', 'guess_mimetype', []);
    }

    get warnAboutCall() {
        return this.nameChanged && this.isSupportedMimetype;
    }

    get nameChanged() {
        return this.state.name !== this.pageName;
    }

    get isSupportedMimetype() {
        const ext = '.' + this.pageName.split('.').pop();
        return ext in this.supportedMimetypes && ext !== '.html';
    }
}
PageNameField.components = {PageDependencies};
PageNameField.template = 'website.PageNameField';
PageNameField.props = {
    ...standardFieldProps,
    placeholder: {type: String, optional: true},
};
PageNameField.extractProps = ({attrs}) => {
    return {
        placeholder: attrs.placeholder,
    };
};
PageNameField.supportedTypes = ['char'];

registry.category("fields").add("page_name", PageNameField);

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
