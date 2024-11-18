import options from "@web_editor/js/editor/snippets.options";
import weUtils from "@web_editor/js/common/utils";
import "@website/js/editor/snippets.options";
import { _t } from "@web/core/l10n/translation";
import { memoize } from "@web/core/utils/functions";
import { renderToElement } from "@web/core/utils/render";

options.registry.WebsiteSignupFieldEditor = options.Class.extend({
    init: function () {
        this._super.apply(this, arguments);
        this.rerender = true;
        this._getVisibilityConditionCachedRecords = memoize(
            (model, domain, fields, kwargs = {}) => {
                return this.orm.searchRead(model, domain, fields, {
                    ...kwargs,
                    limit: 1000, // Safeguard to not crash DBs
                });
            },
        );
    },
    start: async function () {
        const _super = this._super.bind(this);
        // Build the custom select
        const select = this._getSelect();
        if (select) {
            const field = this._getActiveField();
            await this._replaceField(field);
        }
        return _super(...arguments);
    },
    _renderCustomXML: function() {
        // working on this 
    },
    _getActiveField: function (noRecords) {
        let field;
        const labelText = this.$target.find('.signup_form_label_content').text();
        field = Object.assign({}, this.fields[this._getFieldName()]);
        field.string = labelText;
        field.type = this._getFieldType();

        if (!noRecords) {
            field.records = this._getListItems();
        }
        this._setActiveProperties(field);
        return field;
    },
    _replaceField: async function (field) {
        await this._fetchFieldRecords(field);
        const activeField = this._getActiveField();
        if (activeField.type !== field.type) {
            field.value = '';
        }
        const fieldEl = this._renderField(field);
        this._replaceFieldElement(fieldEl);
    },
    _replaceFieldElement(fieldEl) {
        const inputEl = this.$target[0].querySelector('input');
        const dataFillWith = inputEl ? inputEl.dataset.fillWith : undefined;
        [...this.$target[0].childNodes].forEach(node => node.remove());
        [...fieldEl.childNodes].forEach(node => this.$target[0].appendChild(node));
        [...fieldEl.attributes].forEach(el => this.$target[0].removeAttribute(el.nodeName));
        [...fieldEl.attributes].forEach(el => this.$target[0].setAttribute(el.nodeName, el.nodeValue));
        const newInputEl = this.$target[0].querySelector('input');
        if (newInputEl) {
            newInputEl.dataset.fillWith = dataFillWith;
        }
    },
    _fetchFieldRecords: async function (field) {
        field.required = field.required ? 1 : null;
        if (field.records) {
            return field.records;
        }
        return field.records;
    },
    _getFieldName: function () {
        return this.$target[0].querySelector('.signup_form_input').name;
    },
    _getFieldType: function () {
        return this.$target[0].dataset.type;
    },
    _getListItems(removeEmptyValue) {
        const select = this._getSelect();
        let options = [];
        if (select) {
            options = [...select.querySelectorAll('option')];
            if (
                removeEmptyValue &&
                options.length &&
                options[0].value === "" &&
                options[0].textContent === "" &&
                options[0].selected === true
            ) {
                options.shift();
            }
        }
        return options.map(opt => {
            const name = select ? opt : opt.nextElementSibling;
            return {
                id: /^-?[0-9]{1,15}$/.test(opt.value) ? parseInt(opt.value) : opt.value,
                display_name: name.textContent.trim(),
                selected: select ? opt.selected : opt.checked,
            };
        });
    },
    _getSelect: function () {
        return this.$target[0].querySelector('select');
    },
});

options.registry.WebsiteSignupFormFieldRequired = options.Class.extend({
    async _renderCustomXML(uiFragment) {
        const isRequired = this.$target[0].classList.contains("signup_form_required_field");
        if (isRequired) {
            const fieldName = this.$target[0].querySelector("input").getAttribute("name");
            const spanEl = document.createElement("span");
            spanEl.innerText = _t(`The field “%(field)s” is mandatory for the signup”.`, {
                field: fieldName,
            });
            uiFragment.querySelector("we-alert").appendChild(spanEl);
        }
    },
});

options.registry.AddSignupField = options.Class.extend({
    isTopOption: true,
    isTopFirstOption: true,

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------
    _getQuotesEncodedName(name) {
        return name.replaceAll(/"/g, character => `&quot;`);
    },
    _renderField: function (field, resetId = false) {
        if (!field.id) {
            field.id = weUtils.generateHTMLId();
        }
        const params = { field: { ...field } };
        if (["char", "number", "tel"].includes(field.type)) {
            params.field.inputType = field.type;
        }
        const template = document.createElement('template');
        const element = renderToElement("website.signup_form_field_char",  params )
        template.content.append(element);
        template.content.querySelectorAll("[name]").forEach(el => {
            el.name = this._getQuotesEncodedName(el.name);
        });
        template.content.querySelectorAll("[data-name]").forEach(el => {
            el.dataset.name = this._getQuotesEncodedName(el.dataset.name);
        });
        return template.content.firstElementChild;
    },
    _getDefaultFormat: function () {
        return {
            labelWidth: this.$target[0].querySelector('.signup_form_label')?.style.width || "200px",
            requiredMark: this.$target[0].classList.contains('o_mark_required'),
            optionalMark: this.$target[0].classList.contains('o_mark_optional'),
            mark: this.$target[0].dataset.mark,
        };
    },

    _getCustomField: function (type, name) {
        return {
            name: name,
            string: name,
            custom: true,
            type: type,
        };
    },
    /**
     * Add a char field at the end of the form.
     * New field is set as active
     */
    addField: async function (previewMode, value, params) {
        const field = this._getCustomField('char', 'Custom Text');
        field.formatInfo = this._getDefaultFormat();
        const fieldEl = this._renderField(field);
        this.$target.find('.signup_form_field:last').after(fieldEl);
        this.trigger_up('activate_snippet', {
            $snippet: $(fieldEl),
        });
    },
});
