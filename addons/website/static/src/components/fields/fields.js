/** @odoo-module **/

import {PageDependencies} from '@website/components/dialog/page_properties';
import {standardFieldProps} from '@web/views/fields/standard_field_props';
import {useInputField} from '@web/views/fields/input_field_hook';
import {useService} from '@web/core/utils/hooks';
import {Switch} from '@website/components/switch/switch';
import {registry} from '@web/core/registry';
import {TranslationButton} from "@web/views/fields/translation_button";
import { _t } from '@web/core/l10n/translation';
import { Component, useState, onWillStart } from "@odoo/owl";
import { user } from "@web/core/user";

/**
 * Displays website page dependencies and URL redirect options when the page URL
 * is updated.
 */
class PageUrlField extends Component {
    static components = { Switch, PageDependencies, TranslationButton };
    static template = "website.PageUrlField";
    static props = {
        ...standardFieldProps,
        placeholder: { type: String, optional: true },
    };

    setup() {
        this.websiteService = useService("website");
        this.orm = useService('orm');
        this.serverUrl = `${window.location.origin}/`;

        this.state = useState({
            redirect_old_url: false,
            url: this.fieldURL,
            redirect_type: '301',
            original_url: '',
            url_translate: '',
        });
        onWillStart(async () => {
            const { resModel, resId } = this.props.record;
            const resField = this.props.name;
            // The default website lang is the one of the metadata or the
            // current one otherwise.
            this.defaultWebsiteLangCode = this.websiteService.currentWebsite.metadata.lang;
            const defaultWebsiteLang = this.websiteService.currentWebsite.metadata.defaultLangName;
            if (defaultWebsiteLang) {
                const installedLangInfos = await this.orm.call("res.lang", "get_installed" , []);
                this.defaultWebsiteLangCode = installedLangInfos.find(installedLangInfo => installedLangInfo[1].includes(defaultWebsiteLang.trim()))[0];
            }
            // Retrieve the url translations
            const [fieldTranslations] = await this.orm.call(resModel, "get_field_translations", [
                resId,
                resField,
            ]);
            this.urlTranslations = {};
            fieldTranslations.forEach(element => {
                this.urlTranslations[element.lang] = element.value;
            });
            this.state.original_url = this.urlTranslationInWebsiteDefaultLang;
            this.state.url_translate = this.urlTranslationInWebsiteDefaultLang;
            this.isUserLangSameThanWebsite = user.lang == this.defaultWebsiteLangCode;
        });

        useInputField({getValue: () => this.fieldURL});
    }

    get enableRedirect() {
        return this.urlInWebsiteDefaultLangue !== this.state.original_url;
    }

    get urlInWebsiteDefaultLangue() {
        if (this.isUserLangSameThanWebsite) {
            return `/${this.state.url}`;
        }
        return this.urlTranslationInWebsiteDefaultLang;
    }

    onChangeRedirectOldUrl(value) {
        this.state.redirect_old_url = value;
        this.updateValues();
    }

    get fieldURL() {
        const value = this.props.record.data[this.props.name];
        return (value.url !== undefined ? value.url : value).replace(/^\//g, '');
    }

    get urlTranslationInWebsiteDefaultLang() {
        return this.urlTranslations[this.defaultWebsiteLangCode];
    }

    get isTranslatable() {
        return this.props.record.fields[this.props.name].translate;
    }

    updateValues() {
        // HACK: update redirect data from the URL field.
        // TODO: remove this and use a transient model with redirect fields.
        this.props.record.update({ [this.props.name]: this.state });
    }

    updateTranslations(fieldTranslations) {
        // Update the translations with the new values
        fieldTranslations.forEach(element => {
            this.urlTranslations[element.lang] = element.value;
        });
        // Update the url state if the website default language is the same than
        // the user default language.
        if (this.isUserLangSameThanWebsite) {
            this.state.url = this.urlTranslationInWebsiteDefaultLang.substring(1);
        }
        this.state.url_translate = this.urlTranslationInWebsiteDefaultLang;
    }
}

const pageUrlField = {
    component: PageUrlField,
    supportedTypes: ['char'],
    extractProps: ({ attrs }) => ({
        placeholder: attrs.placeholder,
    }),
};

registry.category("fields").add("page_url", pageUrlField);

/**
 * Displays 'Selection' field's values as images to select.
 * Image src for each value can be added using the option 'images' on field XML.
 */
export class ImageRadioField extends Component {
    static template = "website.FieldImageRadio";
    static props = {
        ...standardFieldProps,
        images: { type: Array, element: String },
    };

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
        this.props.record.update({ [this.props.name]: value });
    }
}

export const imageRadioField = {
    component: ImageRadioField,
    supportedOptions: [
        {
            label: _t("Images"),
            name: "images",
            type: "string",
            help: _t("Use an array to list the images to use in the radio selection.")
        }
    ],
    supportedTypes: ['selection'],
    extractProps: ({ options }) => ({
        images: options.images,
    }),
};

registry.category("fields").add("image_radio", imageRadioField);
