import { _t } from "@web/core/l10n/translation";
import { formatAST, toPyValue } from "@web/core/py_js/py_utils";
import { MultiRecordSelector } from "@web/core/record_selectors/multi_record_selector";
import { RecordSelector } from "@web/core/record_selectors/record_selector";
import { Expression } from "@web/core/tree_editor/condition_tree";
import { isId } from "@web/core/tree_editor/utils";
import { imageUrl } from "@web/core/utils/urls";

const getFormat = (val, displayNames) => {
    let text;
    let colorIndex;
    if (isId(val)) {
        if (typeof displayNames[val] !== "string") {
            return null;
        }
        text = displayNames[val];
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

export class DomainSelectorAutocomplete extends MultiRecordSelector {
    static props = {
        ...MultiRecordSelector.props,
        resIds: true, //resIds could be an array of ids or an array of expressions
    };

    getIds(props = this.props) {
        return props.resIds.filter((val) => isId(val));
    }

    getTags(props, displayNames) {
        const tags = [];
        this._indexInResIds = [];
        props.resIds.forEach((val, index) => {
            const format = getFormat(val, displayNames);
            if (!format) {
                return;
            }
            this._indexInResIds.push(index);
            const len = tags.length;
            const { text, colorIndex } = format;
            tags.push({
                text,
                colorIndex,
                onDelete: () => this.deleteTag(len),
                img:
                    this.isAvatarModel &&
                    isId(val) &&
                    imageUrl(this.props.resModel, val, "avatar_128"),
            });
        });
        return tags;
    }

    deleteTag(index) {
        super.deleteTag(this._indexInResIds[index]);
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
