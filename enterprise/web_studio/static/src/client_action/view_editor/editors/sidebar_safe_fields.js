/** @odoo-module */

/**
 * A list of field widget keys of the wowl's field registry (`registry.category("fields")`)
 * that are safe for the user to swith to when editing a field's properties in the view editor's sidebar.
 *
 * Other widgets either don't make sense for that use because they are too specific, or they need
 * specific implementation details provided by some view to be usable.
 */
export const SIDEBAR_SAFE_FIELDS = [
    "badge",
    "selection_badge",
    "handle",
    "percentpie",
    "radio",
    "selection",
    "image_url",
    "ace",
    "priority",
    "date",
    "datetime",
    "remaining_days",
    "email",
    "phone",
    "url",
    "binary",
    "image",
    "pdf_viewer",
    "boolean",
    "state_selection",
    "boolean_toggle",
    "statusbar",
    "float",
    "float_time",
    "integer",
    "monetary",
    "percentage",
    "progressbar",
    "text",
    "boolean_favorite",
    "boolean_icon",
    "char",
    "statinfo",
    "html",
    "text_emojis",
    "CopyClipboardChar",
    "CopyClipboardURL",
    "char_emojis",
    "many2many_tags",
    "many2one",
    "many2many",
    "one2many",
    "sms_widget",
    "reference",
    "daterange",
];
