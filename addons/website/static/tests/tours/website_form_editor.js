/** @odoo-module **/

    import { queryOne } from "@odoo/hoot-dom";
    import wTourUtils from "@website/js/tours/tour_utils";

    // Visibility possible values:
    const VISIBLE = 'Always Visible';
    const HIDDEN = 'Hidden';
    const CONDITIONALVISIBILITY = 'Visible only if';

    const NB_NON_ESSENTIAL_REQUIRED_FIELDS_IN_DEFAULT_FORM = 2;
    const ESSENTIAL_FIELDS_VALID_DATA_FOR_DEFAULT_FORM = [
        {
            name: 'email_from',
            value: 'admin@odoo.com',
        },
        {
            name: 'subject',
            value: 'Hello, world!',
        }
    ];
    const essentialFieldsForDefaultFormFillInSteps = [];
    for (const data of ESSENTIAL_FIELDS_VALID_DATA_FOR_DEFAULT_FORM) {
        essentialFieldsForDefaultFormFillInSteps.push({
            content: "Enter data in model-required field",
            trigger: `:iframe .s_website_form_model_required .s_website_form_input[name="${data.name}"]`,
            run: `edit ${data.value}`,
        });
    }

    // Replace all `"` character by `&quot;`, all `'` character by `&apos;` and
    // all "`" character by `&lsquo;`.
    const getQuotesEncodedName = function (name) {
            return name.replaceAll(/"/g, character => `&quot;`)
                       .replaceAll(/'/g, character => `&apos;`)
                       .replaceAll(/`/g, character => `&lsquo;`)
                       .replaceAll("\\", character => `&bsol;`);
    };

    const triggerFieldByLabel = (label) => {
        return `.s_website_form_field.s_website_form_custom:has(label:contains("${label}"))`;
    };
    const selectFieldByLabel = (label) => {
        return [{
            content: `Select field "${label}"`,
            trigger: ":iframe " + triggerFieldByLabel(label),
        }];
    };
    const selectButtonByText = function (text) {
        return [{
            content: "Open the select",
            trigger: `we-select:has(we-button:contains("${text}")) we-toggler`,
        },
        {
            content: "Click on the option",
            trigger: `we-select we-button:contains("${text}")`,
        }];
    };
    const selectButtonByData = function (data) {
        return [{
            content: "Open the select",
            trigger: `we-select:has(we-button[${data}]) we-toggler`,
        }, {
            content: "Click on the option",
            trigger: `we-select we-button[${data}]`,
        }];
    };
    const addField = function (name, type, label, required, isCustom,
                               display = {visibility: VISIBLE, condition: ""}) {
        const data = isCustom ? `data-custom-field="${name}"` : `data-existing-field="${name}"`;
        const ret = [{
            content: "Select form",
            extra_trigger: ':iframe .s_website_form_field',
            trigger: ':iframe section.s_website_form',
        }, {
            content: "Add field",
            trigger: 'we-button[data-add-field]',
        },
        ...selectButtonByData(data),
        {
            content: "Wait for field to load",
            trigger: `:iframe .s_website_form_field[data-type="${name}"],:iframe .s_website_form_input[name="${name}"]`, //custom or existing field
            run: function () {},
        },
        ...selectButtonByText(display.visibility),
    ];
        let testText = ':iframe .s_website_form_field';
        if (display.condition) {
            ret.push({
                content: "Set the visibility condition",
                trigger: 'we-input[data-attribute-name="visibilityCondition"] input',
                run: `edit ${display.condition}`,
            });
        }
        if (required) {
            testText += '.s_website_form_required';
            ret.push({
                content: "Mark the field as required",
                trigger: 'we-button[data-name="required_opt"] we-checkbox',
            });
        }
        if (label) {
            testText += `:has(label:contains(${label}))`;
            ret.push({
                content: "Change the label text",
                trigger: 'we-input[data-set-label-text] input',
                run: `edit ${label}`,
            });
        }
        if (type !== 'checkbox' && type !== 'radio' && type !== 'select') {
            let inputType = type === 'textarea' ? type : `input[type="${type}"]`;
            const nameAttribute = isCustom && label ? getQuotesEncodedName(label) : name;
            testText += `:has(${inputType}[name="${nameAttribute}"]${required ? "[required]" : ""})`;
        }
        ret.push({
            content: "Check the resulting field",
            trigger: testText,
            run: function () {},
        });
        return ret;
    };
    const addCustomField = function (name, type, label, required, display) {
        return addField(name, type, label, required, true, display);
    };
    const addExistingField = function (name, type, label, required, display) {
        return addField(name, type, label, required, false, display);
    };

    wTourUtils.registerWebsitePreviewTour("website_form_editor_tour", {
        url: '/',
        edition: true,
        test: true,
    }, () => [
        // Drop a form builder snippet and configure it
        {
            content: "Drop the form snippet",
            trigger: '#oe_snippets .oe_snippet .oe_snippet_thumbnail[data-snippet=s_website_form]',
            run: 'drag_and_drop_native :iframe #wrap',
        }, {
            content: "Select form by clicking on an input field",
            extra_trigger: ':iframe .s_website_form_field',
            trigger: ':iframe section.s_website_form input',
            run: "click",
        }, {
            content: "Verify that the form editor appeared",
            trigger: '.o_we_customize_panel .snippet-option-WebsiteFormEditor',
            run: () => null,
        },
        wTourUtils.goBackToBlocks(),
        {
            content: "Select form by clicking on a text area",
            extra_trigger: ':iframe .s_website_form_field',
            trigger: ':iframe section.s_website_form textarea',
            run: "click",
        }, {
            content: "Verify that the form editor appeared",
            trigger: '.o_we_customize_panel .snippet-option-WebsiteFormEditor',
            run: () => null,
        }, {
            content: "Rename and leave the field label",
            trigger: 'we-input[data-set-label-text] input',
            run: "edit Renamed && blur",
        },
        wTourUtils.goBackToBlocks(),
        {
            content: "Select form itself (not a specific field)",
            extra_trigger: ':iframe .s_website_form_field',
            trigger: ':iframe section.s_website_form',
        },
        ...selectButtonByText('Send an E-mail'),
        {
            content: "Form has a model name",
            trigger: ':iframe section.s_website_form form[data-model_name="mail.mail"]',
        }, {
            content: 'Edit the Phone Number field',
            trigger: ':iframe input[name="phone"]',
            run: "click",
        }, {
            content: 'Change the label position of the phone field',
            trigger: 'we-button[data-select-label-position="right"]',
        },
        ...addCustomField("char", "text", "Conditional Visibility Check 1", false),
        ...addCustomField("char", "text", "Conditional Visibility Check 2", false),
        ...selectButtonByData("data-set-visibility='conditional'"),
        ...selectButtonByData("data-set-visibility-dependency='Conditional Visibility Check 1'"),
        ...addCustomField("char", "text", "Conditional Visibility Check 2", false),
        ...selectFieldByLabel("Conditional Visibility Check 1"),
        ...selectButtonByData("data-set-visibility='conditional'"),
        {
            content: "Check that 'Conditional Visibility Check 2' is not in the list of the visibility selector of Conditional Visibility Check 1",
            trigger: "we-select[data-name='hidden_condition_opt']:not(:has(we-button[data-set-visibility-dependency='Conditional Visibility Check 2']))",
            run: () => null,
        },
        ...addCustomField("char", "text", "Conditional Visibility Check 3", false),
        ...addCustomField("char", "text", "Conditional Visibility Check 4", false),
        ...selectButtonByData("data-set-visibility='conditional'"),
        ...selectButtonByData("data-set-visibility-dependency='Conditional Visibility Check 3'"),
        {
            content: "Change the label of 'Conditional Visibility Check 4' and change it to 'Conditional Visibility Check 3'",
            trigger: 'we-input[data-set-label-text] input',
            run: "edit Conditional Visibility Check 3 && blur",
        },
        {
            content: "Check that the conditional visibility of the renamed field is removed",
            trigger: "we-customizeblock-option.snippet-option-WebsiteFieldEditor we-select:contains('Visibility'):has(we-toggler:contains('Always Visible'))",
            run: () => null,
        },
        ...addCustomField("char", "text", "Conditional Visibility Check 5", false),
        ...addCustomField("char", "text", "Conditional Visibility Check 6", false),
        ...selectButtonByData("data-set-visibility='conditional'"),
        {
            content: "Change the label of 'Conditional Visibility Check 6' and change it to 'Conditional Visibility Check 5'",
            trigger: 'we-input[data-set-label-text] input',
            run: "edit Conditional Visibility Check 5 && blur",
        },
        {
            content: "Check that 'Conditional Visibility Check 5' is not in the list of the renamed field",
            trigger: "we-customizeblock-option.snippet-option-WebsiteFieldEditor we-select[data-name='hidden_condition_opt']:not(:has(we-button:contains('Conditional Visibility Check 5')))",
            run: () => null,
        },
        ...addExistingField('email_cc', 'text', 'Test conditional visibility', false, {visibility: CONDITIONALVISIBILITY, condition: 'odoo'}),
        {
            content: "Ensure that the description has correctly been added on the field",
            trigger: ":iframe .s_website_form_field:contains('Test conditional visibility') .s_website_form_field_description",
            isCheck: true,
        },
        // Check that visibility condition is deleted on dependency type change.
        ...addCustomField("char", "text", "dependent", false, {visibility: CONDITIONALVISIBILITY}),
        ...addCustomField("selection", "radio", "dependency", false),
        ...selectFieldByLabel("dependent"),
        ...selectButtonByData('data-set-visibility-dependency="dependency"'),
        ...selectFieldByLabel("dependency"),
        ...selectButtonByData('data-custom-field="char"'),
        ...selectFieldByLabel("dependent"),
        {
            content: "Open the select",
            trigger: 'we-select:has(we-button[data-set-visibility="visible"]) we-toggler',
        },
        {
            content: "Check that the field no longer has conditional visibility",
            trigger: "we-select we-button[data-set-visibility='visible'].active",
            isCheck: true,
        },

        ...addExistingField('date', 'text', 'Test Date', true),

        ...addExistingField('record_name', 'text', 'Awesome Label', false, {visibility: HIDDEN}),

        ...addExistingField('body_html', 'textarea', 'Your Message', true),

        ...addExistingField('recipient_ids', 'checkbox'),

        ...addCustomField('one2many', 'checkbox', 'Products', true),
        {
            content: "Change Option 1 label",
            trigger: 'we-list table input:eq(0)',
            run: "edit Iphone",
        }, {
            content: "Change Option 2 label",
            trigger: 'we-list table input:eq(1)',
            run: "edit Galaxy S",
        },{
            content: "Change first Option 3 label",
            trigger: 'we-list table input:eq(2)',
            run: "edit Xperia",
        },
        {
            // TODO: Fix code to avoid this behavior
            content: "Click outside focused element before click on add new checkbox otherwise button does'nt work",
            trigger: "we-list we-title",
            run: "click",
        },
        {
            content: "Click on Add new Checkbox",
            trigger: 'we-list we-button.o_we_list_add_optional',
            run: "click",
        },
        {
            content: "Change added Option label",
            trigger: 'we-list table input:eq(3)',
            run: "edit Wiko Stairway",
        }, {
            content: "Check the resulting field",
            trigger: ":iframe .s_website_form_field.s_website_form_custom.s_website_form_required" +
                        ":has(.s_website_form_multiple[data-display='horizontal'])" +
                        ":has(.checkbox:has(label:contains('Iphone')):has(input[type='checkbox'][required]))" +
                        ":has(.checkbox:has(label:contains('Galaxy S')):has(input[type='checkbox'][required]))" +
                        ":has(.checkbox:has(label:contains('Xperia')):has(input[type='checkbox'][required]))" +
                        ":has(.checkbox:has(label:contains('Wiko Stairway')):has(input[type='checkbox'][required]))",
            run: function () {},
        },
        ...selectButtonByData('data-multi-checkbox-display="vertical"'),
        {
            content: "Check the resulting field",
            trigger: ":iframe .s_website_form_field.s_website_form_custom.s_website_form_required" +
                        ":has(.s_website_form_multiple[data-display='vertical'])" +
                        ":has(.checkbox:has(label:contains('Iphone')):has(input[type='checkbox'][required]))" +
                        ":has(.checkbox:has(label:contains('Galaxy S')):has(input[type='checkbox'][required]))" +
                        ":has(.checkbox:has(label:contains('Xperia')):has(input[type='checkbox'][required]))" +
                        ":has(.checkbox:has(label:contains('Wiko Stairway')):has(input[type='checkbox'][required]))",
            run: function () {},
        },

        ...addCustomField('selection', 'radio', 'Service', true),
        {
            content: "Change Option 1 label",
            trigger: 'we-list table input:eq(0)',
            run: "edit After-sales Service",
        }, {
            content: "Change Option 2 label",
            trigger: 'we-list table input:eq(1)',
            run: "edit Invoicing Service",
        }, {
            content: "Change first Option 3 label",
            trigger: 'we-list table input:eq(2)',
            run: "edit Development Service",
        }, 
        {
            // TODO: Fix code to avoid this behavior
            content: "Click outside focused element before click on add new checkbox otherwise button does'nt work",
            trigger: "we-list we-title",
            run: "click",
        },
        {
            content: "Click on Add new Checkbox",
            trigger: 'we-list we-button.o_we_list_add_optional',
        }, {
            content: "Change last Option label",
            trigger: 'we-list table input:eq(3)',
            run: "edit Management Service",
        }, {
            content: "Mark the field as not required",
            trigger: 'we-button[data-name="required_opt"] we-checkbox',
        }, {
            content: "Check the resulting field",
            trigger: ":iframe .s_website_form_field.s_website_form_custom:not(.s_website_form_required)" +
                        ":has(.radio:has(label:contains('After-sales Service')):has(input[type='radio']:not([required])))" +
                        ":has(.radio:has(label:contains('Invoicing Service')):has(input[type='radio']:not([required])))" +
                        ":has(.radio:has(label:contains('Development Service')):has(input[type='radio']:not([required])))" +
                        ":has(.radio:has(label:contains('Management Service')):has(input[type='radio']:not([required])))",
            run: function () {},
        },

        ...addCustomField('many2one', 'select', 'State', true),

        // Customize custom selection field
        {
            content: "Change Option 1 Label",
            trigger: 'we-list table input:eq(0)',
            run: "edit Germany",
        }, {
            content: "Change Option 2 Label",
            trigger: 'we-list table input:eq(1)',
            run: "edit Belgium",
        }, {
            content: "Change first Option 3 label",
            trigger: 'we-list table input:eq(2)',
            run: "edit France",
        }, 
        {
            // TODO: Fix code to avoid this behavior
            content: "Click outside focused element before click on add new checkbox otherwise button does'nt work",
            trigger: "we-list we-title",
            run: "click",
        },
        {
            content: "Click on Add new Checkbox",
            trigger: 'we-button.o_we_list_add_optional',
            run: "click",
        }, 
        {
            // TODO: Fix code to avoid this behavior
            content: "Click outside focused element before click on add new checkbox otherwise button does'nt work",
            trigger: "we-list we-title",
            run: "click",
        },
        {
            content: "Change last Option label",
            trigger: 'we-list table input:eq(3)',
            // TODO: Fix code to avoid blur event
            run: "edit Canada",
        }, {
            content: "Remove Germany Option",
            trigger: '.o_we_select_remove_option:eq(0)',
        }, 
        {
            // TODO: Fix code to avoid this behavior
            content: "Click outside focused element before click on add new checkbox otherwise button does'nt work",
            trigger: "we-list we-title",
            run: "click",
        },
        {
            content: "Click on Add new Checkbox",
            trigger: 'we-list we-button.o_we_list_add_optional',
        }, {
            content: "Change last option label with a number",
            trigger: 'we-list table input:eq(3)',
            run: "edit 44 - UK",
        }, {
            content: "Check that the input value is the full option value",
            trigger: 'we-list table input:eq(3)',
            run: () => {
                const addedOptionEl = document.querySelector('iframe.o_iframe').contentDocument.querySelector('.s_website_form_field select option[value="44 - UK"]');
                if (!addedOptionEl) {
                    console.error('The number option was not correctly added');
                }
            },
        }, {
            content: "Check the resulting snippet",
            trigger: ":iframe .s_website_form_field.s_website_form_custom.s_website_form_required" +
                        ":has(label:contains('State'))" +
                        ":has(select[required]:hidden)" +
                        ":has(.s_website_form_select_item:contains('Belgium'))" +
                        ":has(.s_website_form_select_item:contains('France'))" +
                        ":has(.s_website_form_select_item:contains('Canada'))" +
                        ":has(.s_website_form_select_item:contains('44 - UK'))" +
                        ":not(:has(.s_website_form_select_item:contains('Germany')))",
            run: function () {},
        },

        ...addExistingField('attachment_ids', 'file', 'Invoice Scan'),

        {
            content: "Insure the history step of the editor is not checking for unbreakable",
            trigger: ':iframe #wrapwrap',
            run: () => {
                const wysiwyg = $('iframe:not(.o_ignore_in_tour)').contents().find('#wrapwrap').data('wysiwyg');
                wysiwyg.odooEditor.historyStep(true);
            },
        },
        // Edit the submit button using linkDialog.
        {
            content: "Click submit button to show edit popover",
            trigger: ':iframe .s_website_form_send',
        }, {
            content: "Click on Edit Link in Popover",
            trigger: ':iframe .o_edit_menu_popover .o_we_edit_link',
        }, {
            content: "Check that no URL field is suggested",
            trigger: '.oe-toolbar:not(.oe-floating):has(#url_row:hidden)',
            run: () => null,
        }, {
            content: "Change button's style",
            trigger: '.dropdown:has([name="link_style_color"]) > button',
            run: () => {
                queryOne('.dropdown:has([name="link_style_color"]) > button').click();
                queryOne('[data-value="secondary"]').click();
                queryOne('.dropdown:has([name="link_style_shape"]) > button').click();
                queryOne('[data-value="rounded-circle"]').click();
                queryOne('.dropdown:has([name="link_style_size"]) > button').click();
                queryOne('[data-value="sm"]').click();
            },
        }, {
            content: "Check the resulting button",
            trigger: ':iframe .s_website_form_send.btn.btn-sm.btn-secondary.rounded-circle',
            run: () => null,
        },
        // Add a default value to a auto-fillable field.
        {
            content: 'Select the name field',
            trigger: ':iframe .s_website_form_field:eq(0)',
        }, {
            content: 'Set a default value to the name field',
            trigger: 'we-input[data-attribute-name="value"] input',
            run: "edit John Smith",
        },

        // Add two fields: the 1st one's visibility is tied to the 2nd one
        // being set, and the 2nd one is autopopulated. As a result, both
        // should be visible by default.
        ...addCustomField("char", "text", "field A", false, {visibility: CONDITIONALVISIBILITY}),
        ...addCustomField("char", "text", "field B", false),
        ...selectFieldByLabel("field A"),
        ...selectButtonByData('data-set-visibility-dependency="field B"'),
        ...selectButtonByData('data-select-data-attribute="set"'),
        ...selectFieldByLabel("field B"),
        {
            content: "Insert default value",
            trigger: 'we-input[data-attribute-name="value"] input',
            run: "edit prefilled",
        },
        ...wTourUtils.clickOnSave(),
        {
            content: 'Verify value attribute and property',
            trigger: ':iframe .s_website_form_field:eq(0) input[value="John Smith"]:value("Mitchell Admin")',
        },
        {
            content: 'Verify that phone field is still auto-fillable',
            trigger: ':iframe .s_website_form_field input[data-fill-with="phone"]:value("+1 555-555-5555")',
        },
        // Check that the resulting form behavior is correct.
        {
            content: "Check that field B prefill text is set",
            trigger: `:iframe ${triggerFieldByLabel("field B")}:has(input[value="prefilled"])`,
            isCheck: true,
        }, {
            content: "Check that field A is visible",
            trigger: `:iframe .s_website_form:has(${triggerFieldByLabel("field A")}:visible)`,
            isCheck: true,
        },
        // A) Check that if we edit again and save again the default value is
        // not deleted.
        // B) Add a 3rd field. Field A's visibility is tied to field B being set,
        // field B is autopopulated and its visibility is tied to field C being
        // set, and field C is empty.
        ...wTourUtils.clickOnEditAndWaitEditMode(),
        {
            content: 'Edit the form',
            trigger: ':iframe .s_website_form_field:eq(0) input',
            run: 'click',
        },
        ...addCustomField("char", "text", "field C", false),
        ...selectFieldByLabel("field B"),
        ...selectButtonByText(CONDITIONALVISIBILITY),
        ...selectButtonByText(CONDITIONALVISIBILITY),
        {
            content: "Check that there is a comparator after two clicks on 'Visible only if'",
            trigger: "[data-attribute-name='visibilityComparator']",
            run: function () {
                if (!this.anchor.querySelector("we-button.active")) {
                    console.error("A default comparator should be set");
                }
            },
        },
        ...selectButtonByData('data-set-visibility-dependency="field C"'),
        ...selectButtonByData('data-select-data-attribute="set"'),
        ...wTourUtils.clickOnSave(),

        // Check that the resulting form behavior is correct.
        {
            content: 'Verify that the value has not been deleted',
            trigger: ':iframe .s_website_form_field:eq(0) input[value="John Smith"]',
        }, {
            content: "Check that fields A and B are not visible and that field B's prefill text is still set",
            trigger: ":iframe .s_website_form" +
                `:has(${triggerFieldByLabel("field A")}:not(:visible))` +
                `:has(${triggerFieldByLabel("field B")}` +
                `:has(input[value="prefilled"]):not(:visible))`,
            isCheck: true,
        }, {
            content: "Type something in field C",
            trigger: `:iframe ${triggerFieldByLabel("field C")} input`,
            run: "edit Sesame",
        }, {
            content: "Check that fields A and B are visible",
            trigger: `:iframe .s_website_form:has(${triggerFieldByLabel("field B")}:visible)` +
                `:has(${triggerFieldByLabel("field A")}:visible)`,
            isCheck: true,
        },

        // Have field A's visibility tied to field B containing something,
        // while field B's visibility is also tied to another field.
        ...wTourUtils.clickOnEditAndWaitEditMode(),
        ...selectFieldByLabel("field A"),
        {
            content: "Verify that the form editor appeared",
            trigger: ".o_we_customize_panel .snippet-option-WebsiteFormEditor",
            run: () => null,
        },
        ...selectButtonByData('data-select-data-attribute="contains"'),
        {
            content: "Tie the visibility of field A to field B containing 'peek-a-boo'",
            trigger: "we-input[data-name=hidden_condition_additional_text] input",
            run: "edit peek-a-boo",
        },
        ...wTourUtils.clickOnSave(),

        // Check that the resulting form works and does not raise an error.
         {
            content: "Write anything in C",
            trigger: `:iframe ${triggerFieldByLabel("field C")} input`,
            run: "edit Mellon",
        }, {
            content: "Check that field B is visible, but field A is not",
            trigger: `:iframe .s_website_form:has(${triggerFieldByLabel("field B")}:visible)` +
                `:has(${triggerFieldByLabel("field A")}:not(:visible))`,
            isCheck: true,
        }, {
            content: "Insert 'peek-a-boo' in field B",
            trigger: `:iframe ${triggerFieldByLabel("field B")} input`,
            run: "edit peek-a-boo",
        }, {
            content: "Check that field A is visible",
            trigger: `:iframe .s_website_form:has(${triggerFieldByLabel("field A")}:visible)`,
            isCheck: true,
        },
        ...wTourUtils.clickOnEditAndWaitEditMode(),
        // This step is to ensure select fields are properly cleaned before
        // exiting edit mode
        {
            content: "Click on the select field",
            trigger: ":iframe .s_website_form_field select",
        },
        {
            content: 'Click on the submit button',
            trigger: ':iframe .s_website_form_send',
            extra_trigger: ":iframe .s_website_form_field .row :has(#editable_select)",
            run: 'click',
        },
        {
            content: 'Change the Recipient Email',
            trigger: '[data-field-name="email_to"] input',
            run: "edit test@test.test && blur we-title",
        },
        // Test a field visibility when it's tied to another Date [Time] field
        // being set.
        ...addCustomField("char", "text", "field D", false, { visibility: CONDITIONALVISIBILITY }),
        ...addCustomField("date", "text", "field E", false),
        ...selectFieldByLabel("field D"),
        ...selectButtonByData('data-set-visibility-dependency="field E"'),
        ...selectButtonByData('data-select-data-attribute="after"'),
        {
            content: "Enter a date in the date input",
            trigger: "[data-name='hidden_condition_additional_date'] input",
            run: "edit 03/28/2017",
        },
        ...wTourUtils.clickOnSave(),
        {
            content: "Enter an invalid date in field E",
            trigger: `:iframe ${triggerFieldByLabel("field E")} input`,
            run() {
                this.anchor.value = "25071981";
                this.anchor.dispatchEvent(new InputEvent("input", {bubbles: true}));
                // Adds a delay to let the input code run.
                setTimeout(() => {
                    this.anchor.classList.add("invalidDate");
                }, 500);
            },
        },
        {
            content: "Enter an valid date in field E",
            trigger: `:iframe ${triggerFieldByLabel("field E")} input.invalidDate`,
            run() {
                this.anchor.classList.remove("invalidDate");
                this.anchor.value = "07/25/1981";
                this.anchor.dispatchEvent(new InputEvent("input", {bubbles: true}));
                // Adds a delay to let the input code run.
                setTimeout(() => {
                    this.anchor.classList.add("validDate");
                }, 500);
            },
        },
        {
            content: "Click to open the date picker popover from field E",
            trigger: `:iframe ${triggerFieldByLabel("field E")} input.validDate`,
            run(actions) {
                this.anchor.classList.remove("validDate");
                actions.click();
            },
        },
        {
            content: "Select today's date from the date picker",
            trigger: ":iframe .o_datetime_picker .o_date_item_cell.o_today",
        },
        {
            content: "Check that field D is visible",
            trigger: `:iframe .s_website_form:has(${triggerFieldByLabel("field D")}:visible)`,
            isCheck: true,
        },
        ...wTourUtils.clickOnEditAndWaitEditMode(),
        // The next four calls to "addCustomField" are there to ensure such
        // characters do not make the form editor crash.
        ...addCustomField("char", "text", "''", false),
        ...addCustomField("char", "text", '""', false),
        ...addCustomField("char", "text", "``", false),
        ...addCustomField("char", "text", "\\", false),

        // Ensure that the description option is working as wanted.
        ...addCustomField("char", "text", "Check description option", false),
        wTourUtils.changeOption("WebsiteFieldEditor", "we-button[data-toggle-description] we-checkbox"),
        {
            content: "Ensure that the description has correctly been added on the field",
            trigger: ":iframe .s_website_form_field:contains('Check description option') .s_website_form_field_description",
            isCheck: true,
        },

        ...wTourUtils.clickOnSave(),
        {
            content: 'Verify that the recipient email has been saved',
            // We have to this that way because the input type = hidden.
            trigger: ':iframe form:has(input[name="email_to"][value="test@test.test"])',
            isCheck: true,
        },
        {
            content: "Verify that the selects have been cleaned",
            trigger: ":iframe .s_website_form",
            run() {
                if (
                    this.anchor.querySelector(
                        ".s_website_form_field .row:has(select) #editable_select"
                    )
                ) {
                    console.error("The form was not properly cleaned and still has some editable elements.");
                }
            }
        }
    ]);

    function editContactUs(steps) {
        return [
            {
                content: "Select the contact us form by clicking on an input field",
                trigger: ':iframe .s_website_form input',
                extra_trigger: '#oe_snippets .oe_snippet_thumbnail',
                run: 'click',
            },
            ...steps,
            ...wTourUtils.clickOnSave(),
        ];
    }

    wTourUtils.registerWebsitePreviewTour('website_form_contactus_edition_with_email', {
        url: '/contactus',
        edition: true,
        test: true,
    }, () => editContactUs([
        {
            content: 'Change the Recipient Email',
            trigger: '[data-field-name="email_to"] input',
            run: "edit test@test.test && blur",
        },
    ]));
    wTourUtils.registerWebsitePreviewTour('website_form_contactus_edition_no_email', {
        url: '/contactus',
        edition: true,
        test: true,
    }, () => editContactUs([
        {
            content: "Change a random option",
            trigger: '[data-set-mark] input',
            run: "edit ** && blur",
        }, {
            content: "Check that the recipient email is correct",
            trigger: 'we-input[data-field-name="email_to"] input:value("website_form_contactus_edition_no_email@mail.com")',
            isCheck: true,
        },
    ]));

    wTourUtils.registerWebsitePreviewTour('website_form_conditional_required_checkboxes', {
        test: true,
        url: '/',
        edition: true,
    }, () => [
        // Create a form with two checkboxes: the second one required but
        // invisible when the first one is checked. Basically this should allow
        // to have: both checkboxes are visible by default but the form can
        // only be sent if one of the checkbox is checked.
        {
            content: "Add the form snippet",
            trigger: '#oe_snippets .oe_snippet .oe_snippet_thumbnail[data-snippet=s_website_form]',
            run: 'drag_and_drop_native :iframe #wrap',
        }, {
            content: "Select the form by clicking on an input field",
            extra_trigger: ':iframe .s_website_form_field',
            trigger: ':iframe section.s_website_form input',
            run: function (actions) {
                actions.click();

                // The next steps will be about removing non essential required
                // fields. For the robustness of the test, check that amount
                // of field stays the same.
                const requiredFields = this.anchor.closest("[data-snippet]").querySelectorAll(".s_website_form_required");
                if (requiredFields.length !== NB_NON_ESSENTIAL_REQUIRED_FIELDS_IN_DEFAULT_FORM) {
                    console.error('The amount of required fields seems to have changed');
                }
            },
        },
        ...((function () {
            const steps = [];
            for (let i = 0; i < NB_NON_ESSENTIAL_REQUIRED_FIELDS_IN_DEFAULT_FORM; i++) {
                steps.push({
                    content: "Select required field to remove",
                    trigger: ':iframe .s_website_form_required .s_website_form_input',
                    run: "click",
                });
                steps.push({
                    content: "Remove required field",
                    trigger: ':iframe .oe_overlay .oe_snippet_remove',
                });
            }
            return steps;
        })()),
        ...addCustomField('boolean', 'checkbox', 'Checkbox 1', false),
        ...addCustomField('boolean', 'checkbox', 'Checkbox 2', true, {visibility: CONDITIONALVISIBILITY}),
        {
            content: "Open condition item select",
            trigger: 'we-select[data-name="hidden_condition_opt"] we-toggler',
        }, {
            content: "Choose first checkbox as condition item",
            trigger: 'we-button[data-set-visibility-dependency="Checkbox 1"]',
        }, {
            content: "Open condition comparator select",
            trigger: 'we-select[data-attribute-name="visibilityComparator"] we-toggler',
        }, {
            content: "Choose 'not equal to' comparator",
            trigger: 'we-button[data-select-data-attribute="!selected"]',
        },
        ...wTourUtils.clickOnSave(),

        // Check that the resulting form behavior is correct
        {
            content: "Wait for page reload",
            trigger: ':iframe body:not(.editor_enable) [data-snippet="s_website_form"]',
            run: function (actions) {
                // The next steps will be about removing non essential required
                // fields. For the robustness of the test, check that amount
                // of field stays the same.
                const essentialFields = this.anchor.querySelectorAll(".s_website_form_model_required");
                if (essentialFields.length !== ESSENTIAL_FIELDS_VALID_DATA_FOR_DEFAULT_FORM.length) {
                    console.error('The amount of model-required fields seems to have changed');
                }
            },
        },
        ...essentialFieldsForDefaultFormFillInSteps,
        {
            content: 'Try sending empty form',
            trigger: ':iframe .s_website_form_send',
        }, {
            content: 'Check the form could not be sent',
            trigger: ':iframe #s_website_form_result.text-danger',
            run: () => null,
        }, {
            content: 'Check the first checkbox',
            trigger: ':iframe input[type="checkbox"][name="Checkbox 1"]',
        }, {
            content: 'Check the second checkbox is now hidden',
            trigger: ':iframe .s_website_form:has(input[type="checkbox"][name="Checkbox 2"]:not(:visible))',
            run: () => null,
        }, {
            content: 'Try sending the form',
            trigger: ':iframe .s_website_form_send',
        }, {
            content: "Check the form was sent (success page without form)",
            trigger: ':iframe body:not(:has([data-snippet="s_website_form"])) .fa-check-circle',
            run: () => null,
        }, {
            content: "Go back to the form",
            trigger: ':iframe a.navbar-brand.logo',
        },
        ...essentialFieldsForDefaultFormFillInSteps,
        {
            content: 'Check the second checkbox',
            trigger: ':iframe input[type="checkbox"][name="Checkbox 2"]',
        }, {
            content: 'Try sending the form again',
            trigger: ':iframe .s_website_form_send',
        }, {
            content: "Check the form was again sent (success page without form)",
            trigger: ':iframe body:not(:has([data-snippet="s_website_form"])) .fa-check-circle',
            run: () => null,
        }
    ]);

    wTourUtils.registerWebsitePreviewTour('website_form_contactus_change_random_option', {
        test: true,
        url: '/contactus',
        edition: true,
    }, () => editContactUs([
        {
            content: "Change a random option",
            trigger: '[data-set-mark] input',
            run: "edit ** && blur",
        },
    ]));

    export default {};
