/** @odoo-module alias=@web/../tests/core/domain_selector_tests default=false */

import {
    SELECTORS as treeEditorSELECTORS,
} from "./condition_tree_editor_helpers";

export {
    addNewRule,
    clearNotSupported,
    clickOnButtonAddBranch,
    clickOnButtonAddNewRule,
    clickOnButtonDeleteNode,
    editValue,
    getConditionText,
    getCurrentOperator,
    getCurrentPath,
    getCurrentValue,
    getOperatorOptions,
    isNotSupportedOperator,
    isNotSupportedPath,
    isNotSupportedValue,
    selectOperator,
    selectValue,
    toggleArchive,
} from "./condition_tree_editor_helpers";

export const SELECTORS = {
    ...treeEditorSELECTORS,
    debugArea: ".o_domain_selector_debug_container textarea",
    resetButton: ".o_domain_selector_row > button",
};
