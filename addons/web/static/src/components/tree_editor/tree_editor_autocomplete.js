// @ts-check

/** @module @web/components/tree_editor/tree_editor_autocomplete - Record autocomplete variants for single and multi-value domain/expression editors */

import { MultiRecordSelector } from "@web/components/record_selectors/multi_record_selector";
import { RecordSelector } from "@web/components/record_selectors/record_selector";
import { Expression } from "@web/components/tree_editor/condition_tree";
import { isId } from "@web/components/tree_editor/utils";
import { _t } from "@web/core/l10n/translation";
import { formatAST } from "@web/core/py_js/py";
import { toPyValue } from "@web/core/py_js/py_utils";
import { imageUrl } from "@web/core/utils/urls";
/**
 * Formats a record value for display as a tag, with color coding for validity.
 * @param {number|import("./condition_tree").Expression|any} val
 * @param {Record<number, string>} displayNames
 * @returns {{text: string, colorIndex: number}} display text and color (0=grey, 1=red, 2=orange)
 */
const getFormat = (val, displayNames) => {
    let text;
    let colorIndex;
    if (isId(val)) {
        text =
            typeof displayNames[val] === "string"
                ? displayNames[val]
                : _t("Inaccessible/missing record ID: %s", val);
        colorIndex = typeof displayNames[val] === "string" ? 0 : 2; // 0 = grey, 2 = orange
    } else {
        text =
            val instanceof Expression
                ? String(val)
                : _t("Invalid record ID: %s", formatAST(toPyValue(val)));
        colorIndex = val instanceof Expression ? 2 : 1; // 1 = red
    }
    return { text, colorIndex };
};

// @ts-expect-error - OWL Component static props typing
export class DomainSelectorAutocomplete extends MultiRecordSelector {
    static props = {
        ...MultiRecordSelector.props,
        resIds: true, //resIds could be an array of ids or an array of expressions
    };

    /**
     * @param {Object} [props]
     * @returns {number[]} only valid record IDs from resIds
     */
    getIds(props = this.props) {
        return props.resIds.filter((val) => isId(val));
    }

    /**
     * @param {Object} props
     * @param {Record<number, string>} displayNames
     * @returns {Array<{text: string, colorIndex: number, onDelete: Function, img: string|false}>}
     */
    getTags(props, displayNames) {
        return props.resIds.map((val, index) => {
            const { text, colorIndex } = getFormat(val, displayNames);
            return {
                text,
                colorIndex,
                onDelete: () => {
                    this.props.update([
                        ...this.props.resIds.slice(0, index),
                        ...this.props.resIds.slice(index + 1),
                    ]);
                },
                img:
                    this.isAvatarModel &&
                    isId(val) &&
                    imageUrl(this.props.resModel, val, "avatar_128"),
            };
        });
    }
}

// @ts-expect-error - OWL Component static props typing
export class DomainSelectorSingleAutocomplete extends RecordSelector {
    static props = {
        ...RecordSelector.props,
        resId: true,
    };

    /**
     * @param {Object} [props]
     * @param {Record<number, string>} [displayNames]
     * @returns {string}
     */
    getDisplayName(props = this.props, displayNames) {
        const { resId } = props;
        if (resId === false) {
            return "";
        }
        const { text } = getFormat(resId, displayNames);
        return text;
    }

    /**
     * @param {Object} [props]
     * @returns {number[]}
     */
    getIds(props = this.props) {
        if (isId(props.resId)) {
            return [props.resId];
        }
        return [];
    }
}
