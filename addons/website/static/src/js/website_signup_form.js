import options from "@web_editor/js/editor/snippets.options";
import { _t } from "@web/core/l10n/translation";

options.registry.WebsiteSignupFormEditor = options.Class.extend({
    async start () {
        
    }
});

options.registry.WebsiteSignupFormFieldRequired = options.Class.extend({
    async _renderCustomXML(uiFragment) {
        const isRequired = this.$target[0].classList.contains("signup_form_required_field");
        if (isRequired) {
            const fieldName = this.$target[0].getAttribute("name");
            const spanEl = document.createElement("span");
            spanEl.innerText = _t(`The field “%(fieldName)s” is mandatory for the signup”.`, {
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

    /**
     * Add a char field with active field properties after the active field.
     * New field is set as active
     */
    addField: async function (previewMode, value, params) {
        this.trigger_up('option_update', {
            optionName: 'WebsiteSignupFormEditor',
            name: 'add_field',
            data: {
                // formatInfo: this._getFieldFormat(),
                $target: this.$target,
            },
        });
    },
});
