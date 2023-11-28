/** @odoo-module **/

import { Component, onWillStart, onWillUpdateProps } from "@odoo/owl";
import { doFormatValue } from "@web/core/tree_editor/condition_tree";
import { Editor, getEditorInfo } from "@web/core/editors/editor";
import { registry } from "@web/core/registry";
import { TagsList } from "@web/core/tags_list/tags_list";

function getText(value, isSupported, serialize, component) {
    return isSupported(value) ? serialize(value, component) : doFormatValue(value);
}

function getTexts(array, isSupported, serialize, component) {
    return Promise.all(array.map((val) => getText(val, isSupported, serialize, component)));
}

class ListEditor extends Component {
    static components = { TagsList, Editor };
    static props = {
        update: Function,
        value: Array,
        isSupported: Function,
        serialize: Function,
        subType: String,
        "*": true,
    };
    static template = "web.ListEditor";

    setup() {
        onWillStart(() => this.computeDerivedParams(this.props));
        onWillUpdateProps((nextProps) => this.computeDerivedParams(nextProps));
    }

    async computeDerivedParams(props) {
        const { isSupported, serialize, value, update } = props;

        const tagTexts = await getTexts(value, isSupported, serialize, this);
        this.tags = value.map((val, index) => ({
            text: tagTexts[index],
            colorIndex: isSupported(val) ? 0 : 2,
            onDelete: () => {
                update([...value.slice(0, index), ...value.slice(index + 1)]);
            },
        }));

        this.editorProps = {
            ...props,
            type: props.subType,
            multiSelect: true,
            currentValues: value,
            className: "flex-grow-1",
            value: false,
            update: (...newValues) => {
                props.update([...value, ...newValues]);
            },
        };
    }
}

registry.category("editors").add("list", (genericProps) => {
    const { subType } = genericProps;
    const { isSupported, serialize } = getEditorInfo(subType, { ...genericProps, type: subType });
    return {
        component: ListEditor,
        props: { ...genericProps, isSupported, serialize },
        defaultValue: () => [],
        isSupported: Array.isArray,
    };
});
