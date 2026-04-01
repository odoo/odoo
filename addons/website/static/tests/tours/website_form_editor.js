import {
    changeOption,
    clickOnEditAndWaitEditMode,
    clickOnSave,
    insertSnippet,
    goBackToBlocks,
    registerWebsitePreviewTour,
    changeOptionInPopover,
} from "@website/js/tours/tour_utils";
import { stepUtils } from "@web_tour/tour_utils";
import { editorsWeakMap } from "@html_editor/../tests/tours/helpers/editor";

// Visibility possible values:
const VISIBLE = "Always Visible";
const CONDITIONALVISIBILITY = "Visible only if";

const NB_NON_ESSENTIAL_REQUIRED_FIELDS_IN_DEFAULT_FORM = 2;
const ESSENTIAL_FIELDS_VALID_DATA_FOR_DEFAULT_FORM = [
    {
        name: "email_from",
        value: "admin@odoo.com",
    },
    {
        name: "subject",
        value: "Hello, world!",
    },
];
const essentialFieldsForDefaultFormFillInSteps = [];
for (const data of ESSENTIAL_FIELDS_VALID_DATA_FOR_DEFAULT_FORM) {
    essentialFieldsForDefaultFormFillInSteps.push({
        content: "Enter data in model-required field",
        trigger: `:iframe .s_website_form_model_required .s_website_form_input[name="${data.name}"]`,
        run: `edit ${data.value} && press Tab`,
    });
    essentialFieldsForDefaultFormFillInSteps.push({
        trigger: `:iframe .s_website_form_model_required .s_website_form_input[name="${data.name}"]:value(${data.value})`,
    });
}

// Replace all `"` character by `&quot;`.
const getQuotesEncodedName = function (name) {
    return name.replaceAll(/"/g, (character) => `&quot;`);
};

const triggerFieldByLabel = (label) =>
    `.s_website_form_field.s_website_form_custom:has(label:contains("${label}"))`;
const selectFieldByLabel = (label) => [
    {
        content: `Select field "${label}"`,
        trigger: ":iframe " + triggerFieldByLabel(label),
        run: "click",
    },
];
const selectButtonByText = function (text, dropdownContent) {
    return [
        {
            content: "Open the select",
            trigger: `.o_customize_tab button:contains('${text}')`,
            run: "click",
        },
        {
            content: "Click on the option",
            trigger: `.o_popover div.dropdown-item:contains('${dropdownContent}')`,
            run: "click",
        },
    ];
};
const selectButtonByData = function (text, data) {
    return [
        {
            content: "Open the select",
            trigger: `.o_customize_tab button:contains('${text}')`,
            run: "click",
        },
        {
            content: "Click on the option",
            trigger: `.o_popover ${data}`,
            run: "click",
        },
    ];
};
const addField = function (
    name,
    type,
    label,
    required,
    isCustom,
    display = { visibility: VISIBLE, condition: "" }
) {
    const data = isCustom
        ? `[data-action-id='customField'][data-action-value='${name}']`
        : `[data-action-id='existingField'][data-action-value='${name}']`;
    const ret = [
        {
            trigger: ":iframe .s_website_form_field",
        },
        {
            content: "Select form",
            trigger: ":iframe section.s_website_form",
            run: "click",
        },
        {
            content: "Add field",
            trigger: "[data-container-title=Form] button:contains('+ Field')",
            run: "click",
        },
        ...selectButtonByData("Text", data),
        {
            content: "Wait for field to load",
            trigger: `:iframe .s_website_form_field[data-type="${name}"],:iframe .s_website_form_input[name="${name}"]`, //custom or existing field
        },
        ...changeOptionInPopover("Field", "Visibility", display.visibility),
    ];
    let testText = ":iframe .s_website_form_field";
    if (display.condition) {
        ret.push({
            content: "Set the visibility condition",
            trigger: ".o_customize_tab [data-name='hidden_condition_additional_text'] input",
            run: `edit ${display.condition} && press Tab`,
        });
    }
    if (required) {
        testText += ".s_website_form_required";
        ret.push({
            content: "Mark the field as required",
            trigger: ".o_customize_tab div[data-action-id='toggleRequired'] input[type='checkbox']",
            run: "click",
        });
    }
    if (label) {
        testText += `:has(label:contains(${label}))`;
        ret.push({
            content: "Change the label text",
            trigger: ".o_customize_tab div[data-action-id='setLabelText'] input",
            run: `edit ${label} && press Tab`,
        });
    }
    if (type !== "checkbox" && type !== "radio" && type !== "select") {
        const inputType = type === "textarea" ? type : `input[type="${type}"]`;
        const nameAttribute = isCustom && label ? getQuotesEncodedName(label) : name;
        testText += `:has(${inputType}[name="${CSS.escape(nameAttribute)}"]${
            required ? "[required]" : ""
        })`;
    }
    ret.push({
        content: "Check the resulting field",
        trigger: testText,
    });
    return ret;
};
const addCustomField = function (name, type, label, required, display) {
    return addField(name, type, label, required, true, display);
};
const addExistingField = function (name, type, label, required, display) {
    return addField(name, type, label, required, false, display);
};
const compareIds = ({ content, firstElSelector, secondElSelector, errorMessage }) => ({
    content,
    trigger: `:iframe ${firstElSelector}`,
    run: function () {
        const firstEl = this.anchor;
        const secondEl = firstEl.ownerDocument.querySelector(secondElSelector);
        if (firstEl.id === secondEl.id) {
            console.error(errorMessage);
        }
    },
});

registerWebsitePreviewTour(
    "website_form_editor_tour",
    {
        url: "/",
        edition: true,
    },
    () => [
        // Drop a form builder snippet and configure it
        ...insertSnippet({
            id: "s_title_form",
            name: "Contact & Forms",
            groupName: "Contact & Forms",
        }),
        {
            trigger: ":iframe .s_website_form_field",
        },
        {
            content: "Select form by clicking on an input field",
            trigger: ":iframe .s_website_form_field .s_website_form_input",
            run: "click",
        },
        {
            content: "Verify that the form editor appeared",
            trigger: ".o_customize_tab div[data-container-title='Form']",
        },
        goBackToBlocks(),
        {
            trigger: ":iframe .s_website_form_field",
        },
        {
            content: "Select form by clicking on a text area",
            trigger: ":iframe .s_website_form_field textarea.s_website_form_input",
            run: "click",
        },
        {
            content: "Verify that the form editor appeared",
            trigger: ".o_customize_tab div[data-container-title='Form']",
        },
        {
            content: "Rename and leave the field label",
            trigger: ".o_customize_tab div[data-action-id='setLabelText'] input",
            run: "edit Renamed && click body",
        },
        goBackToBlocks(),
        {
            trigger: ":iframe .s_website_form_field",
        },
        {
            content: "Select form itself (not a specific field)",
            trigger: ":iframe section.s_website_form",
            run: "click",
        },
        ...changeOptionInPopover("Form", "Action", "Send an E-mail"),
        {
            content: "Form has a model name",
            trigger: ':iframe section.s_website_form form[data-model_name="mail.mail"]',
            run: "click",
        },
        {
            content: "Set the offset and width of the Phone Number field",
            trigger: ':iframe input[name="phone"]',
            run: function () {
                const fieldEl = this.anchor.closest(".s_website_form_field");
                fieldEl.classList.add("offset-lg-3");
                fieldEl.classList.add("col-lg-9");
            },
        },
        {
            content: "Edit the Phone Number field",
            trigger: ':iframe input[name="phone"]',
            run: "click",
        },
        {
            content: "Change the label position of the phone field",
            trigger:
                ".o_customize_tab div[data-label='Position'] button[data-action-value='right']",
            run: "click",
        },
        ...addCustomField("char", "text", "Conditional Visibility Check 1", false),
        ...addCustomField("char", "text", "Conditional Visibility Check 2", false),
        ...changeOptionInPopover("Field", "Visibility", "Visible only if"),
        ...selectButtonByData("Your Name", "[data-action-value='Conditional Visibility Check 1']"),
        ...addCustomField("char", "text", "Conditional Visibility Check 2", false),
        ...selectFieldByLabel("Conditional Visibility Check 1"),
        ...changeOptionInPopover("Field", "Visibility", "Visible only if"),
        {
            content: "Open list of the visibility selector of Conditional Visibility Check 1",
            trigger: ".o_customize_tab button:contains('Your Name')",
            run: "click",
        },
        {
            content:
                "Check that 'Conditional Visibility Check 2' is not in the list of the visibility selector of Conditional Visibility Check 1",
            trigger:
                ".o_popover div:not(:has([data-action-value='Conditional Visibility Check 2']))",
        },
        ...addCustomField("char", "text", "Conditional Visibility Check 3", false),
        ...addCustomField("char", "text", "Conditional Visibility Check 4", false),
        ...changeOptionInPopover("Field", "Visibility", "Visible only if"),
        ...selectButtonByData("Your Name", "[data-action-value='Conditional Visibility Check 3']"),
        {
            content:
                "Change the label of 'Conditional Visibility Check 4' and change it to 'Conditional Visibility Check 3'",
            trigger: ".o_customize_tab div[data-action-id='setLabelText'] input",
            // TODO: remove && click body
            run: "edit Conditional Visibility Check 3 && click body",
        },
        {
            content: "Check that the conditional visibility of the renamed field is removed",
            trigger: ".o_customize_tab [data-label='Visibility'] button:contains('Always Visible')",
        },
        ...addCustomField("char", "text", "Conditional Visibility Check 5", false),
        ...addCustomField("char", "text", "Conditional Visibility Check 6", false),
        ...changeOptionInPopover("Field", "Visibility", "Visible only if"),
        {
            content:
                "Change the label of 'Conditional Visibility Check 6' and change it to 'Conditional Visibility Check 5'",
            trigger: ".o_customize_tab div[data-action-id='setLabelText'] input",
            // TODO: remove && click body
            run: "edit Conditional Visibility Check 5 && click body",
        },
        {
            content: "Open list of the visibility selector of Conditional Visibility Check 1",
            trigger: ".o_customize_tab button:contains('Your Name')",
            run: "click",
        },
        {
            content:
                "Check that 'Conditional Visibility Check 5' is not in the list of the renamed field",
            trigger:
                ".o_popover div:not(:has([data-action-value='Conditional Visibility Check 5']))",
        },
        ...addExistingField("email_cc", "text", "Test conditional visibility", false, {
            visibility: CONDITIONALVISIBILITY,
            condition: "odoo",
        }),
        {
            content: "Ensure that the description has correctly been added on the field",
            trigger:
                ":iframe .s_website_form_field:contains('Test conditional visibility') .s_website_form_field_description",
        },
        // Check that visibility condition is deleted on dependency type change.
        ...addCustomField("char", "text", "dependent", false, {
            visibility: CONDITIONALVISIBILITY,
        }),
        ...addCustomField("selection", "radio", "dependency", false),
        ...selectFieldByLabel("dependent"),
        ...selectButtonByData("Your Name", "[data-action-value='dependency']"),
        ...selectFieldByLabel("dependency"),
        ...selectButtonByData("Radio Buttons", "[data-action-value='char']"),
        ...selectFieldByLabel("dependent"),
        {
            content: "Open the select",
            trigger: ".o_customize_tab button:contains('Always Visible')",
            run: "click",
        },
        {
            content: "Check that the field no longer has conditional visibility",
            trigger: ".o_popover div[data-action-value='visible'].active",
        },

        ...addExistingField("date", "text", "Test Date", true),

        ...addExistingField("body_html", "textarea", "Your Message", true),

        ...addExistingField("recipient_ids", "checkbox"),

        ...addCustomField("one2many", "checkbox", "Products", true),
        {
            content: "Change Option 1 label",
            trigger: ".o_we_table_wrapper table input[name='display_name']:eq(0)",
            run: "edit Iphone && press Tab",
        },
        {
            content: "Change Option 2 label",
            trigger: ".o_we_table_wrapper table input[name='display_name']:eq(1)",
            run: "edit Galaxy S && press Tab",
        },
        {
            content: "Change first Option 3 label",
            trigger: ".o_we_table_wrapper table input[name='display_name']:eq(2)",
            run: "edit Xperia && press Tab",
        },
        {
            content: "Click on Add new Checkbox",
            trigger: "button.builder_list_add_item",
            run: "click",
        },
        {
            content: "Change added Option label",
            trigger: ".o_we_table_wrapper table input[name='display_name']:eq(3)",
            run: "edit Wiko Stairway && press Tab",
        },
        {
            content: "Check the resulting field",
            trigger:
                ":iframe .s_website_form_field.s_website_form_custom.s_website_form_required" +
                ":has(.s_website_form_multiple[data-display='horizontal'])" +
                ":has(.checkbox:has(label:contains('Iphone')):has(input[type='checkbox'][required]))" +
                ":has(.checkbox:has(label:contains('Galaxy S')):has(input[type='checkbox'][required]))" +
                ":has(.checkbox:has(label:contains('Xperia')):has(input[type='checkbox'][required]))" +
                ":has(.checkbox:has(label:contains('Wiko Stairway')):has(input[type='checkbox'][required]))",
        },
        ...selectButtonByData("Horizontal", "[data-action-value='vertical']"),
        {
            content: "Check the resulting field",
            trigger:
                ":iframe .s_website_form_field.s_website_form_custom.s_website_form_required" +
                ":has(.s_website_form_multiple[data-display='vertical'])" +
                ":has(.checkbox:has(label:contains('Iphone')):has(input[type='checkbox'][required]))" +
                ":has(.checkbox:has(label:contains('Galaxy S')):has(input[type='checkbox'][required]))" +
                ":has(.checkbox:has(label:contains('Xperia')):has(input[type='checkbox'][required]))" +
                ":has(.checkbox:has(label:contains('Wiko Stairway')):has(input[type='checkbox'][required]))",
        },
        // Check conditional visibility for the relational fields
        ...changeOptionInPopover("Field", "Visibility", "Visible only if"),
        ...selectButtonByData("Your Name", "[data-action-value='recipient_ids']"),
        ...selectButtonByText("Is equal to", "Is not equal to"),
        {
            content: "Click on option to change the partner for visiblity condition",
            trigger: "[data-name='hidden_condition_additional_text'] button",
            run: "click",
        },
        {
            content: "Click on option to change the partner for visiblity condition",
            trigger: ".o_popover div[role='menuitem']:contains('Mitchell Admin')",
            run: "click",
        },
        ...clickOnSave(),
        {
            content: "Check 'products' field is visible.",
            trigger: `:iframe .s_website_form:has(${triggerFieldByLabel("Products")}:visible)`,
        },
        {
            content: "choose the option 'Mitchell Admin' of partner.",
            trigger:
                ":iframe .checkbox:has(label:contains('Mitchell Admin')) input[type='checkbox']",
            run: "click",
        },
        {
            content: "Check 'products' field is not visible.",
            trigger:
                ":iframe .s_website_form" +
                `:has(${triggerFieldByLabel("Products")}:not(:visible))`,
        },
        ...clickOnEditAndWaitEditMode(),
        ...addCustomField("selection", "radio", "Service", true),
        {
            content: "Change Option 1 label",
            trigger: ".o_we_table_wrapper table input[name='display_name']:eq(0)",
            run: "edit After-sales Service && press Tab",
        },
        {
            content: "Change Option 2 label",
            trigger: ".o_we_table_wrapper table input[name='display_name']:eq(1)",
            run: "edit Invoicing Service && press Tab",
        },
        {
            content: "Change first Option 3 label",
            trigger: ".o_we_table_wrapper table input[name='display_name']:eq(2)",
            run: "edit Development Service && press Tab",
        },
        {
            content: "Click on Add new Checkbox",
            trigger: "button.builder_list_add_item",
            run: "click",
        },
        {
            content: "Change last Option label",
            trigger: ".o_we_table_wrapper table input[name='display_name']:eq(3)",
            run: "edit Management Service",
        },
        {
            content: "Mark the field as not required",
            trigger: "div[data-action-id='toggleRequired'] input[type='checkbox']",
            run: "click",
        },
        {
            content: "Check the resulting field",
            trigger:
                ":iframe .s_website_form_field.s_website_form_custom:not(.s_website_form_required)" +
                ":has(.radio:has(label:contains('After-sales Service')):has(input[type='radio']:not([required])))" +
                ":has(.radio:has(label:contains('Invoicing Service')):has(input[type='radio']:not([required])))" +
                ":has(.radio:has(label:contains('Development Service')):has(input[type='radio']:not([required])))" +
                ":has(.radio:has(label:contains('Management Service')):has(input[type='radio']:not([required])))",
        },

        ...addCustomField("many2one", "select", "State", true),

        // Customize custom selection field
        {
            content: "Change Option 1 Label",
            trigger: ".o_we_table_wrapper table input[name='display_name']:eq(0)",
            run: "edit Germany && press Tab",
        },
        {
            content: "Change Option 2 Label",
            trigger: ".o_we_table_wrapper table input[name='display_name']:eq(1)",
            run: "edit Belgium && press Tab",
        },
        {
            content: "Change first Option 3 label",
            trigger: ".o_we_table_wrapper table input[name='display_name']:eq(2)",
            run: "edit France && press Tab",
        },
        {
            content: "Click on Add new Checkbox",
            trigger: "button.builder_list_add_item",
            run: "click",
        },
        {
            content: "Change last Option label",
            trigger: ".o_we_table_wrapper table input[name='display_name']:eq(3)",
            // TODO: Fix code to avoid blur event
            run: "edit Canada && press Tab",
        },
        {
            content: "Remove Germany Option",
            trigger: ".builder_list_remove_item:eq(0)",
            run: "click",
        },
        {
            content: "Click on Add new Checkbox",
            trigger: "button.builder_list_add_item",
            run: "click",
        },
        {
            content: "Change last option label with a number",
            trigger: ".o_we_table_wrapper table input[name='display_name']:eq(3)",
            run: "edit 44 - UK",
        },
        {
            content: "Check that the input value is the full option value",
            trigger: ".o_we_table_wrapper table input[name='display_name']:eq(3)",
            run: () => {
                // We need this 'setTimeout' to ensure that the 'input' event of
                // the input has enough time to be executed (see the
                // '_onListItemBlurInput' function of the 'we-list' widget).
                setTimeout(() => {
                    const addedOptionEl = document
                        .querySelector("iframe")
                        .contentDocument.querySelector(
                            '.s_website_form_field select option[value="44 - UK"]'
                        );
                    if (!addedOptionEl) {
                        console.error("The number option was not correctly added");
                    }
                }, 500);
            },
        },
        {
            content: "Check the resulting snippet",
            trigger:
                ":iframe .s_website_form_field.s_website_form_custom.s_website_form_required" +
                ":has(label:contains('State'))" +
                ":has(select[required])" +
                ":has(option:contains('Belgium')):not([selected])" +
                ":has(option:contains('France'))" +
                ":has(option:contains('Canada'))" +
                ":has(option:contains('44 - UK'))" +
                ":not(:has(option:contains('Germany')))",
        },

        ...addExistingField("attachment_ids", "file", "Invoice Scan"),
        {
            content: "Insure the history step of the editor is not checking for unbreakable",
            trigger: ":iframe #wrapwrap",
            run() {
                const editor = editorsWeakMap.get(this.anchor.ownerDocument);
                editor.shared.history.addStep();
            },
        },
        // Edit the submit button using linkDialog.
        {
            content: "Click submit button to show edit popover",
            trigger: ":iframe .s_website_form_send",
            run: "click",
        },
        {
            content: "Verify that the button options do not have clone/remove/save buttons.",
            trigger:
                "div[data-container-title='Button'] .options-container-header:not(:has(.oe_snippet_remove, .oe_snippet_clone, .oe_snippet_save))",
        },
        {
            content: "Click on Edit Link in Popover",
            trigger: ".o-we-linkpopover .o_we_edit_link",
            run: "click",
        },
        {
            content: "Change button's style",
            trigger: ".o-we-linkpopover select[name='link_type']",
            run: "select custom",
        },
        {
            trigger: ".o-we-linkpopover select[name=link_style_shape]",
            run: "select rounded-circle",
        },
        {
            trigger: ".o-we-linkpopover select[name='link_style_size']",
            run: "select sm",
        },
        {
            trigger: ".o-we-linkpopover .o_we_apply_link",
            run: "click",
        },
        {
            content: "Check the resulting button",
            trigger: ":iframe .s_website_form_send.btn.btn-sm.btn-custom.rounded-circle",
        },
        // Add a default value to a auto-fillable field.
        ...selectFieldByLabel("Your Name"),
        {
            content: "Set a default value to the name field",
            trigger: "[data-label='Default Value'] input",
            run: "edit John Smith",
        },

        // Add two fields: the 1st one's visibility is tied to the 2nd one
        // being set, and the 2nd one is autopopulated. As a result, both
        // should be visible by default.
        ...addCustomField("char", "text", "field A", false, { visibility: CONDITIONALVISIBILITY }),
        ...addCustomField("char", "text", "field B", false),
        ...selectFieldByLabel("field A"),
        ...selectButtonByData("Your Name", "[data-action-value='field B']"),
        ...selectButtonByText("Is equal to", "Is set"),
        ...selectFieldByLabel("field B"),
        {
            content: "Insert default value",
            trigger: "[data-label='Default Value'] input",
            run: "edit prefilled",
        },
        ...clickOnSave(),
        {
            content: "Verify value attribute and property",
            trigger:
                ":iframe .s_website_form_field input[value='John Smith']:value('Mitchell Admin')",
            run: "click",
        },
        {
            content: "Verify that phone field is still auto-fillable",
            trigger:
                ':iframe .s_website_form_field input[data-fill-with="phone"]:value("+1 555-555-5555")',
            run: "click",
        },
        {
            content: "Check that the offset and width of the Phone Number field are still correct",
            trigger: ':iframe .s_website_form_field input[data-fill-with="phone"]',
            run: function () {
                const fieldEl = this.anchor.closest(".s_website_form_field");
                if (!fieldEl.classList.contains("offset-lg-3")) {
                    throw new Error("The offset of the Phone Number field should have been kept");
                }
                if (!fieldEl.classList.contains("col-lg-9")) {
                    throw new Error("The width of the Phone Number field should have been kept");
                }
            },
        },
        // Check that the resulting form behavior is correct.
        {
            content: "Check that field B prefill text is set",
            trigger: `:iframe ${triggerFieldByLabel("field B")}:has(input[value="prefilled"])`,
        },
        {
            content: "Check that field A is visible",
            trigger: `:iframe .s_website_form:has(${triggerFieldByLabel("field A")}:visible)`,
        },
        // A) Check that if we edit again and save again the default value is
        // not deleted.
        // B) Add a 3rd field. Field A's visibility is tied to field B being set,
        // field B is autopopulated and its visibility is tied to field C being
        // set, and field C is empty.
        ...clickOnEditAndWaitEditMode(),
        {
            content: "Edit the form",
            trigger: ":iframe .s_website_form_field input",
            run: "click",
        },
        ...addCustomField("char", "text", "field C", false),
        ...selectFieldByLabel("field B"),
        ...changeOptionInPopover("Field", "Visibility", "Visible only if"),
        {
            content: "Verify that the default comparator should be set",
            trigger: ".o_customize_tab #hidden_condition_opt:not(:empty)",
        },
        ...selectButtonByData("Your Name", "[data-action-value='field C']"),
        ...selectButtonByText("Is equal to", "Is set"),
        ...selectFieldByLabel("field C"),
        ...clickOnSave(),

        // Check that the resulting form behavior is correct.
        {
            content: "Verify that the value has not been deleted",
            trigger: ":iframe .s_website_form_field input[value='John Smith']",
            run: "click",
        },
        {
            content:
                "Check that fields A and B are not visible and that field B's prefill text is still set",
            trigger:
                ":iframe .s_website_form" +
                `:has(${triggerFieldByLabel("field A")}:not(:visible))` +
                `:has(${triggerFieldByLabel("field B")}` +
                `:has(input[value="prefilled"]):not(:visible))`,
        },
        {
            content: "Type something in field C",
            trigger: `:iframe ${triggerFieldByLabel("field C")} input`,
            run: "edit Sesame",
        },
        {
            content: "Check that fields A and B are visible",
            trigger:
                `:iframe .s_website_form:has(${triggerFieldByLabel("field B")}:visible)` +
                `:has(${triggerFieldByLabel("field A")}:visible)`,
        },

        // Have field A's visibility tied to field B containing something,
        // while field B's visibility is also tied to another field.
        ...clickOnEditAndWaitEditMode(),
        ...selectFieldByLabel("field A"),
        {
            content: "Verify that the form editor appeared",
            trigger: ".o_customize_tab div[data-container-title='Form'] .we-bg-options-container",
        },
        ...selectButtonByText("Is set", "Contains"),
        {
            content: "Tie the visibility of field A to field B containing 'peek-a-boo'",
            trigger: "[data-name='hidden_condition_additional_text'] input",
            run: "edit peek-a-boo",
        },
        ...clickOnSave(),

        // Check that the resulting form works and does not raise an error.
        {
            content: "Write anything in C",
            trigger: `:iframe ${triggerFieldByLabel("field C")} input`,
            run: "edit Mellon && press Tab",
        },
        {
            content: "Check that field B is visible, but field A is not",
            trigger:
                `:iframe .s_website_form:has(${triggerFieldByLabel("field B")}:visible)` +
                `:has(${triggerFieldByLabel("field A")}:not(:visible))`,
        },
        {
            content: "Insert 'peek-a-boo' in field B",
            trigger: `:iframe ${triggerFieldByLabel("field B")} input`,
            run: "edit peek-a-boo",
        },
        {
            content: "Check that field A is visible",
            trigger: `:iframe .s_website_form:has(${triggerFieldByLabel("field A")}:visible)`,
        },
        ...clickOnEditAndWaitEditMode(),
        ...addCustomField("char", "text", "Philippe of Belgium", false),
        {
            content: "Select the 'Subject' field",
            trigger:
                ':iframe .s_website_form_field.s_website_form_model_required:has(label:contains("Subject"))',
            run: "click",
        },
        ...changeOptionInPopover("Field", "Visibility", "Visible only if"),
        ...selectButtonByData("Your Name", "[data-action-value='Philippe of Belgium']"),
        ...selectButtonByText("Is equal to", "Is set"),
        {
            content: "Set a default value to the 'Subject' field",
            trigger: "[data-label='Default Value'] input",
            run: "edit Default Subject",
        },
        {
            content: "Select the 'Your Message' field",
            trigger:
                ':iframe .s_website_form_field.s_website_form_required:has(label:contains("Your Message"))',
            run: "click",
        },
        ...changeOptionInPopover("Field", "Visibility", "Visible only if"),
        ...selectButtonByData("Your Name", "[data-action-value='Philippe of Belgium']"),
        ...selectButtonByText("Is equal to", "Is set"),

        ...clickOnSave(),
        // Ensure that a field required for a model is not disabled when
        // conditionally hidden.
        {
            content: "Check that the 'Subject' field is not disabled",
            trigger:
                `:iframe .s_website_form:has(.s_website_form_model_required ` +
                `.s_website_form_input[value="Default Subject"]:not([disabled]):not(:visible))`,
        },
        // Ensure that a required field (but not for a model) is disabled when
        // conditionally hidden.
        {
            content: "Check that the 'Your Message' field is disabled",
            trigger:
                `:iframe .s_website_form:has(.s_website_form_required ` +
                `.s_website_form_input[name="body_html"][required][disabled]:not(:visible))`,
        },

        ...clickOnEditAndWaitEditMode(),
        {
            content: "Select the 'Subject' field",
            trigger:
                ':iframe .s_website_form_field.s_website_form_model_required:has(label:contains("Subject"))',
            run: "click",
        },
        ...changeOptionInPopover("Field", "Visibility", "Always Visible"),
        {
            content: "Empty the default value of the 'Subject' field",
            trigger: "[data-label='Default Value'] input",
            run: "clear",
        },
        {
            content: "Select the 'Your Message' field",
            trigger:
                ':iframe .s_website_form_field.s_website_form_required:has(label:contains("Your Message"))',
            run: "click",
        },
        ...changeOptionInPopover("Field", "Visibility", "Always Visible"),
        // This step is to ensure select fields are properly cleaned before
        // exiting edit mode
        {
            content: "Click on the select field",
            trigger: ":iframe .s_website_form_field select",
            run: "click",
        },
        {
            content: "Click on the submit button",
            trigger: ":iframe .s_website_form_send",
            run: "click",
        },
        {
            content: "Change the Recipient Email",
            trigger: '[data-label="Recipient Email"] input',
            run: "edit test@test.test",
        },
        // Test a field visibility when it's tied to another Date [Time] field
        // being set.
        ...addCustomField("char", "text", "field D", false, { visibility: CONDITIONALVISIBILITY }),
        ...addCustomField("date", "text", "field E", false),
        ...selectFieldByLabel("field D"),
        ...selectButtonByData("Your Name", "[data-action-value='field E']"),
        {
            content: "Open the comparator select",
            trigger: "#hidden_condition_time_comparators_opt",
            run: "click",
        },
        {
            content: "Select the 'Is after' comparator",
            trigger: ".o_popover div[role='menuitem']:contains('Is after')",
            run: "click",
        },
        {
            content: "Enter a date in the date input",
            trigger: "[data-name='hidden_condition_additional_text'] input",
            run: "edit 03/28/2017",
        },
        ...clickOnSave(),
        {
            content: "Enter an invalid date in field E",
            trigger: `:iframe ${triggerFieldByLabel("field E")} input`,
            run() {
                this.anchor.value = "25071981";
                this.anchor.dispatchEvent(new InputEvent("input", { bubbles: true }));
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
                this.anchor.dispatchEvent(new InputEvent("input", { bubbles: true }));
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
            run: "click",
        },
        {
            content: "Check that field D is visible",
            trigger: `:iframe .s_website_form:has(${triggerFieldByLabel("field D")}:visible)`,
        },
        ...clickOnEditAndWaitEditMode(),
        // The next four calls to "addCustomField" are there to ensure such
        // characters do not make the form editor crash.
        ...addCustomField("char", "text", "''", false),
        ...addCustomField("char", "text", '""', false),
        ...addCustomField("char", "text", "``", false),
        ...addCustomField("char", "text", "\\", false),

        // Ensure that the description option is working as wanted.
        ...addCustomField("char", "text", "Check description option", false),
        changeOption("Field", "[data-action-id='toggleDescription'] input"),
        {
            content: "Ensure that the description has correctly been added on the field",
            trigger:
                ":iframe .s_website_form_field:contains('Check description option') .s_website_form_field_description",
        },

        ...clickOnSave(),
        {
            content: "Verify that the recipient email has been saved",
            // We have to this that way because the input type = hidden.
            trigger: ':iframe form:has(input[name="email_to"][value="test@test.test"])',
        },
    ]
);

function editContactUs(steps) {
    return [
        {
            trigger: ".o-website-builder_sidebar .o_snippet_thumbnail",
        },
        {
            content: "Select the contact us form by clicking on an input field",
            trigger: ":iframe .s_website_form input",
            run: "click",
        },
        ...steps,
        ...clickOnSave(),
    ];
}

registerWebsitePreviewTour(
    "website_form_contactus_edition_with_email",
    {
        url: "/contactus",
        edition: true,
    },
    () =>
        editContactUs([
            {
                content: "Change the Recipient Email",
                trigger: "div[data-label='Recipient Email'] input",
                run: "edit test@test.test",
            },
        ])
);
registerWebsitePreviewTour(
    "website_form_contactus_edition_no_email",
    {
        url: "/contactus",
        edition: true,
    },
    () =>
        editContactUs([
            {
                content: "Change a random option",
                trigger: "[data-action-id='setMark'] input",
                run: "edit **",
            },
            {
                content: "Check that the recipient email is correct",
                trigger:
                    "div[data-label='Recipient Email'] input:value('website_form_contactus_edition_no_email@mail.com')",
            },
        ])
);

registerWebsitePreviewTour(
    "website_form_conditional_required_checkboxes",
    {
        url: "/",
        edition: true,
    },
    () => [
        // Create a form with two checkboxes: the second one required but
        // invisible when the first one is checked. Basically this should allow
        // to have: both checkboxes are visible by default but the form can
        // only be sent if one of the checkbox is checked.
        ...insertSnippet({
            id: "s_title_form",
            name: "Title - Form",
            groupName: "Contact & Forms",
        }),
        {
            trigger: ":iframe .s_website_form_field",
        },
        {
            content: "Select the form by clicking on an input field",
            trigger: ":iframe section.s_website_form input",
            async run(actions) {
                await actions.click();

                // The next steps will be about removing non essential required
                // fields. For the robustness of the test, check that amount
                // of field stays the same.
                const requiredFields = this.anchor
                    .closest("[data-snippet]")
                    .querySelectorAll(".s_website_form_required");
                if (requiredFields.length !== NB_NON_ESSENTIAL_REQUIRED_FIELDS_IN_DEFAULT_FORM) {
                    console.error("The amount of required fields seems to have changed");
                }
            },
        },
        ...(function () {
            const steps = [];
            for (let i = 0; i < NB_NON_ESSENTIAL_REQUIRED_FIELDS_IN_DEFAULT_FORM; i++) {
                steps.push({
                    content: "Select required field to remove",
                    trigger: ":iframe .s_website_form_required .s_website_form_input",
                    run: "click",
                });
                steps.push({
                    content: "Remove required field",
                    trigger: ".o_overlay_options .oe_snippet_remove",
                    run: "click",
                });
            }
            return steps;
        })(),
        ...addCustomField("boolean", "checkbox", "Checkbox 1", false),
        ...addCustomField("boolean", "checkbox", "Checkbox 2", true, {
            visibility: CONDITIONALVISIBILITY,
        }),
        {
            content: "Open condition item select",
            trigger: "[data-container-title='Field'] #hidden_condition_opt",
            run: "click",
        },
        {
            content: "Choose first checkbox as condition item",
            trigger: ".o_popover div[role='menuitem'][data-action-value='Checkbox 1']",
            run: "click",
        },
        {
            content: "Open condition comparator select",
            trigger: "[data-container-title='Field'] #hidden_condition_no_text_opt",
            run: "click",
        },
        {
            content: "Choose 'not equal to' comparator",
            trigger: ".o_popover div[role='menuitem']:contains('not equal to')",
            run: "click",
        },
        ...clickOnSave(),

        // Check that the resulting form behavior is correct
        {
            content: "Wait for page reload",
            trigger: 'body:not(.editor_enable) :iframe [data-snippet="s_website_form"]',
            run: function (actions) {
                // The next steps will be about removing non essential required
                // fields. For the robustness of the test, check that amount
                // of field stays the same.
                const essentialFields = this.anchor.querySelectorAll(
                    ".s_website_form_model_required"
                );
                if (
                    essentialFields.length !== ESSENTIAL_FIELDS_VALID_DATA_FOR_DEFAULT_FORM.length
                ) {
                    console.error("The amount of model-required fields seems to have changed");
                }
            },
        },
        {
            content: "Wait the form is loaded before fill it",
            trigger: ":iframe form:contains(checkbox 2)",
        },
        ...essentialFieldsForDefaultFormFillInSteps,
        {
            content: "Try sending empty form",
            trigger: ":iframe .s_website_form_send",
            run: "click",
        },
        {
            content: "Check the form could not be sent",
            trigger: ":iframe #s_website_form_result.text-danger",
        },
        {
            content: "Check the first checkbox",
            trigger: ":iframe input[type='checkbox'][name='Checkbox 1']",
            run: "click",
        },
        {
            content: "Check the second checkbox is now hidden",
            trigger:
                ":iframe .s_website_form:has(input[type='checkbox'][name='Checkbox 2']:not(:visible))",
        },
        {
            content: "Try sending the form",
            trigger: ":iframe .s_website_form_send",
            run: "click",
        },
        {
            content: "Check the form was sent (success page without form)",
            trigger: ':iframe body:not(:has([data-snippet="s_website_form"])) .fa-paper-plane',
        },
        {
            content: "Go back to the form",
            trigger: ":iframe a.navbar-brand.logo",
            run: "click",
        },
        {
            content: "Wait the form is loaded before fill it",
            trigger: ":iframe form:contains(checkbox 2)",
        },
        ...essentialFieldsForDefaultFormFillInSteps,
        {
            content: "Check the second checkbox",
            trigger: ':iframe input[type="checkbox"][name="Checkbox 2"]',
            run: "click",
        },
        {
            content: "Try sending the form again",
            trigger: ":iframe .s_website_form_send",
            run: "click",
        },
        {
            content: "Check the form was again sent (success page without form)",
            trigger: ':iframe body:not(:has([data-snippet="s_website_form"])) .fa-paper-plane',
        },
    ]
);

registerWebsitePreviewTour(
    "website_form_contactus_change_random_option",
    {
        url: "/contactus",
        edition: true,
    },
    () =>
        editContactUs([
            {
                content: "Change a random option",
                trigger: "[data-action-id='setMark'] input",
                run: "edit **",
            },
        ])
);

registerWebsitePreviewTour(
    "website_form_nested_forms",
    {
        url: "/my/account",
        edition: true,
    },
    () => [
        {
            trigger: ".o-website-builder_sidebar .o_snippets_container .o_snippet",
            noPrepend: true,
        },
        {
            trigger:
                ".o_block_tab:not(.o_we_ongoing_insertion) .o_snippet[name='Form'].o_draggable .o_snippet_thumbnail",
            content: "Try to drag the form into another form",
            run: "drag_and_drop :iframe .o_customer_address_fill a",
        },
        {
            content: "Check the form was not dropped into another form",
            trigger:
                ":iframe form[action='/my/address/submit']:not(:has([data-snippet='s_website_form']))",
            run: () => null,
        },
    ]
);

// Check that the editable form content is actually editable.
registerWebsitePreviewTour(
    "website_form_editable_content",
    {
        url: "/",
        edition: true,
    },
    () => [
        {
            trigger: ".o-snippets-menu div.o_snippet",
        },
        {
            trigger: `.o-snippets-menu .o_block_tab:not(.o_we_ongoing_insertion) .o_snippet[name="Form"].o_draggable .o_snippet_thumbnail`,
            run: "drag_and_drop :iframe #wrap",
        },
        {
            trigger: ":iframe .s_website_form_field",
        },
        {
            content: "Check that a form field is not editable",
            trigger: ":iframe section.s_website_form input",
            run: function () {
                if (this.anchor.isContentEditable) {
                    console.error("A form field should not be editable.");
                }
            },
        },
        goBackToBlocks(),
        ...insertSnippet({ id: "s_three_columns", name: "Columns", groupName: "Columns" }),
        {
            content: "Select the first column",
            trigger: ":iframe .s_three_columns .row > :nth-child(1)",
            run: "click",
        },
        {
            content: "Drag and drop the selected column inside the form",
            trigger: ".o_overlay_options .o_move_handle",
            run: "drag_and_drop :iframe section.s_website_form",
        },
        {
            trigger: ":iframe section.s_website_form .col-lg-4[contenteditable=true]",
        },
        {
            content: "Click on the text inside the dropped form column",
            trigger: ":iframe section.s_website_form h2.card-title",
            run: "dblclick",
        },
        {
            // Simulate a user interaction with the editable content.
            content: "Update the text inside the form column",
            trigger: ":iframe section.s_website_form h2.card-title",
            run: "editor ABC",
        },
        {
            content: "Check that the new text value was correctly set",
            trigger: ":iframe section.s_website_form h2:text(ABC)",
            run() {
                this.anchor.scrollIntoView();
            },
        },
        {
            content: "Remove the dropped column",
            trigger: ".o_overlay_options .oe_snippet_remove",
            run: "click",
        },
        ...clickOnSave(),
    ]
);

registerWebsitePreviewTour(
    "website_form_special_characters",
    {
        url: "/",
        edition: true,
    },
    () => [
        ...insertSnippet({
            id: "s_title_form",
            name: "Title - Form",
            groupName: "Contact & Forms",
        }),
        {
            content: "Select form by clicking on an input field",
            trigger: ":iframe section.s_website_form input",
            run: "click",
        },
        ...addCustomField("char", "text", `Test1"'`, false),
        ...clickOnSave(),
        stepUtils.waitIframeIsReady(),
        ...essentialFieldsForDefaultFormFillInSteps,
        {
            content: "Complete 'Your Question' field",
            trigger: ":iframe textarea[name='description']",
            run: "edit test",
        },
        {
            content: "Complete the first added field",
            trigger: `:iframe input[name="${CSS.escape("Test1&quot;'")}"]`,
            run: "edit test1",
        },
        {
            content: "Click on 'Submit'",
            trigger: ":iframe a.s_website_form_send",
            run: "click",
        },
        {
            content: "Check the form was again sent (success page without form)",
            trigger: ":iframe body:not(:has([data-snippet='s_website_form'])) .fa-paper-plane",
        },
    ]
);

registerWebsitePreviewTour(
    "website_form_duplicate_field_ids",
    {
        url: "/",
        edition: true,
    },
    () => [
        // Fields in two form snippet should have unique IDs
        {
            content: "Drop a form snippet",
            trigger:
                ".o_block_tab:not(.o_we_ongoing_insertion) .o_snippet[name='Form'].o_draggable .o_snippet_thumbnail",
            run: "drag_and_drop :iframe #wrap",
        },
        {
            content: "Check if form snippet is dropped",
            trigger: ":iframe .s_website_form_field",
        },
        ...insertSnippet({
            id: "s_title_form",
            name: "Title - Form",
            groupName: "Contact & Forms",
        }),
        compareIds({
            content: "Check that the first field of both the form snippets have different IDs",
            firstElSelector: ".s_website_form input[name='name']",
            secondElSelector: ".s_title_form .s_website_form input[name='name']",
            errorMessage: "The first fields of two different form snippet have the same ID",
        }),
        {
            content: "Click on the form snippet",
            trigger: ":iframe .s_website_form",
            run: "click",
        },
        {
            content: "Delete the form snippet",
            trigger: "[data-container-title='Form'] .options-container-header .oe_snippet_remove",
            run: "click",
        },
        // Cloning a snippet with form in it should generate new IDs for the
        // cloned form fields.
        {
            content: "Click on 'Title - Form' snippet",
            trigger: ":iframe .s_title_form",
            run: "click",
        },
        {
            content: "Clone the 'Title - Form' snippet",
            trigger:
                "[data-container-title='Title - Form'] .options-container-header .oe_snippet_clone",
            run: "click",
        },
        {
            content: "Check if the form is cloned",
            trigger: ":iframe .s_title_form:nth-of-type(2)",
        },
        compareIds({
            content:
                "Check if the first field of forms in original and cloned snippets have different IDs",
            firstElSelector: ".s_title_form .s_website_form input[name='name']",
            secondElSelector: ".s_title_form:nth-of-type(2) .s_website_form input[name='name']",
            errorMessage: "The first fields of original and cloned form snippet have the same ID",
        }),
        // Cloning a form itself should should generate new IDs for the cloned
        // form fields.
        {
            content: "Click on the form in 'Title - Form' snippet",
            trigger: ":iframe .s_title_form .s_website_form",
            run: "click",
        },
        {
            content: "Clone the form",
            trigger: "[data-container-title='Form'] .options-container-header .oe_snippet_clone",
            run: "click",
        },
        {
            content: "Check if the form is cloned",
            trigger: ":iframe .s_title_form .s_website_form:nth-of-type(2)",
        },
        compareIds({
            content:
                "Check if the first field of original and cloned form snippets have different IDs",
            firstElSelector: ".s_title_form .s_website_form input[name='name']",
            secondElSelector: ".s_title_form .s_website_form:nth-of-type(2) input[name='name']",
            errorMessage: "The first fields of original and cloned form snippet have the same ID",
        }),
        // Cloning a field should generate new ID for the cloned field
        {
            content: "Click on the name field",
            trigger: ":iframe .s_title_form .s_website_form input[name='name']",
            run: "click",
        },
        {
            content: "Clone the name field",
            trigger: "[data-container-title='Field'] .options-container-header .oe_snippet_clone",
            run: "click",
        },
        compareIds({
            content: "Check if both, original and cloned name fields have unique IDs",
            firstElSelector: ".s_title_form .s_website_form input[name='name']",
            secondElSelector: ".s_title_form [data-name='Field']:nth-of-type(3) input[name='name']",
            errorMessage: "Original and cloned fields have the same ID",
        }),
    ]
);
