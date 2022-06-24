/** @odoo-module **/

import {PageDependencies} from '@website/components/dialog/page_properties';
import {Switch} from '@website/components/switch/switch';
import AbstractFieldOwl from 'web.AbstractFieldOwl';
import fieldRegistry from 'web.field_registry_owl';

const {useState, onWillStart} = owl;

class FieldPageUrl extends AbstractFieldOwl {
    setup() {
        super.setup();

        this.state = useState({
            redirect_old_url: false,
            url: this.value,
            redirect_type: '301',
        });

        this.serverUrl = window.location.origin;
        this.pageUrl = this.value;
    }

    get enableRedirect() {
        return this.state.url !== this.pageUrl;
    }

    onChangeRedirectOldUrl(value) {
        this.state.redirect_old_url = value;
    }

    /**
     * @override
     */
    commitChanges() {
        if (this.enableRedirect) {
            this._setValue(this.state);
        }
        return super.commitChanges();
    }
}
FieldPageUrl.components = {Switch, PageDependencies};
FieldPageUrl.supportedFieldTypes = ['char'];
FieldPageUrl.template = 'website.FieldPageUrl';

class FieldPageName extends AbstractFieldOwl {
    setup() {
        super.setup();

        this.state = useState({
            name: this.value,
        });

        this.pageName = this.value;
        this.supportedMimetypes = {};

        onWillStart(() => this.onWillStart());
    }

    async onWillStart() {
        this.supportedMimetypes = await this.rpc({
            model: 'website',
            method: 'guess_mimetype',
        });
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

    /**
     * @override
     */
    commitChanges() {
        if (this.nameChanged) {
            this._setValue(this.state.name);
        }
        return super.commitChanges();
    }
}
FieldPageName.components = {PageDependencies};
FieldPageName.supportedFieldTypes = ['char'];
FieldPageName.template = 'website.FieldPageName';

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

fieldRegistry.add('page_url', FieldPageUrl);
fieldRegistry.add('page_name', FieldPageName);
fieldRegistry.add('fa_prefix', FieldFaPrefix);
