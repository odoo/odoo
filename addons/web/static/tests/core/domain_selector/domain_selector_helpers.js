import { SELECTORS as treeEditorSELECTORS } from "@web/../tests/core/tree_editor/condition_tree_editor_test_helpers";

export const SELECTORS = {
    ...treeEditorSELECTORS,
    debugArea: ".o_domain_selector_debug_container textarea",
    resetButton: ".o_domain_selector_row > button",
};

export const userContext = {
    allowed_company_ids: [1],
    lang: "en",
    tz: "taht",
    uid: 7,
};
