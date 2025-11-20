import { _t } from "@web/core/l10n/translation";
import { formatAST, toPyValue } from "@web/core/py_js/py_utils";
import { MultiRecordSelector } from "@web/core/record_selectors/multi_record_selector";
import { RecordSelector } from "@web/core/record_selectors/record_selector";
import { Expression } from "@web/core/tree_editor/condition_tree";
import { isId } from "@web/core/tree_editor/utils";
import { imageUrl } from "@web/core/utils/urls";

const getFormat = (val, displayNames) => {
    if (isId(val)) {
        const text = typeof displayNames[val] === "string" ? displayNames[val] : String(val);
        const colorIndex = typeof displayNames[val] === "string" ? 0 : 1; // 0 = grey, 1 = red
        const tooltip =
            typeof displayNames[val] === "string" ? text : _t("Missing record (ID: %s)", val);
        return { text, colorIndex, tooltip };
    } else {
        const text =
            val instanceof Expression
                ? String(val)
                : _t("Invalid record ID: %s", formatAST(toPyValue(val)));
        const colorIndex = val instanceof Expression ? 2 : 1; // 1 = red, 2 = orange
        return { text, colorIndex, tooltip: text };
    }
};

export class DomainSelectorAutocomplete extends MultiRecordSelector {
    static props = {
        ...MultiRecordSelector.props,
        resIds: true, //resIds could be an array of ids or an array of expressions
    };

    getIds(props = this.props) {
        return props.resIds.filter((val) => isId(val));
    }

    getTags(props, displayNames) {
        return props.resIds.map((val, index) => {
            const { text, colorIndex, tooltip } = getFormat(val, displayNames);
            return {
                id: val,
                text,
                tooltip,
                color: colorIndex,
                onDelete: () => super.deleteTag(index),
                img:
                    this.isAvatarModel &&
                    isId(val) &&
                    imageUrl(this.props.resModel, val, "avatar_128"),
            };
        });
    }
}

export class DomainSelectorSingleAutocomplete extends RecordSelector {
    static props = {
        ...RecordSelector.props,
        resId: true,
    };

    getDisplayName(props = this.props, displayNames) {
        const { resId } = props;
        if (resId === false) {
            return "";
        }
        const { text } = getFormat(resId, displayNames);
        return text;
    }

    getIds(props = this.props) {
        if (isId(props.resId)) {
            return [props.resId];
        }
        return [];
    }
}
