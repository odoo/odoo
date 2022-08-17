/** @odoo-module **/

import {PageDependencies} from '@website/components/dialog/page_properties';
import {standardFieldProps} from '@web/views/fields/standard_field_props';
import {useInputField} from '@web/views/fields/input_field_hook';
import {useService} from '@web/core/utils/hooks';
import AbstractFieldOwl from 'web.AbstractFieldOwl';
import fieldRegistry from 'web.field_registry_owl';
import {registry} from '@web/core/registry';
import {formatChar} from '@web/views/fields/formatters';

const {Component, useState, onWillStart, useEffect} = owl;

/**
 * Displays website page dependencies when the page URL is updated.
 */
class PageUrlField extends Component {
    setup() {
        this.urlChanged = false;
        this.serverUrl = window.location.origin;
        this.pageUrl = this.props.value.replace(/^\//g, '');
        this.resId = this.props.record.context.active_id;

        this.state = useState({
            url: this.pageUrl,
        });
        useInputField({getValue: () => this.props.value});

        useEffect(
            () => {
                this.urlChanged = this.state.url !== this.pageUrl;
                this.props.update(this.state.url);
            },
            () => [this.state.url]
        );
    }
}
PageUrlField.components = {PageDependencies};
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
        this.resId = this.props.record.context.active_id;

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
 * Displays 'char' field's value prefixed by a FA icon.
 * The prefix is shown by default, but the visibility can be updated depending on
 * other field value.
 * e.g. `<field name="name" widget="fa_prefix" options="{'icon': 'fa-lock',
 * 'visibility': 'is_locked'}"/>` renders the icon only when 'is_locked' is True.
 */
class FieldFaPrefix extends AbstractFieldOwl {
    get prefix() {
        const {icon, visibility, title} = this.nodeOptions;
        return {
            class: icon.split(' ').filter(str => str.indexOf('fa-') === 0).join(' '),
            visible: !visibility || !!this.recordData[visibility],
            help: title || '',
        };
    }
}
FieldFaPrefix.supportedFieldTypes = ['char'];
FieldFaPrefix.template = 'website.FieldFaPrefix';

fieldRegistry.add('fa_prefix', FieldFaPrefix);
