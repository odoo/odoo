import { Component } from "@odoo/owl";
import {
    clickableBuilderComponentProps,
    useActionInfo,
    useLanguageDirection,
    useSelectableItemComponent,
} from "../utils";
import { BuilderComponent } from "./builder_component";
import { Image } from "../img";
import { _t } from "@web/core/l10n/translation";

export class BuilderButton extends Component {
    static template = "html_builder.BuilderButton";
    static components = { BuilderComponent, Image };
    static props = {
        ...clickableBuilderComponentProps,

        title: { type: String, optional: true },
        titleActive: { type: String, optional: true },
        label: { type: String, optional: true },
        iconImg: { type: String, optional: true },
        iconImgAlt: { type: String, optional: true },
        iconImgAttrs: { type: Object, optional: true },
        icon: { type: String, optional: true },
        className: { type: String, optional: true },
        classActive: { type: String, optional: true },
        style: { type: String, optional: true },
        type: { type: String, optional: true },

        slots: { type: Object, optional: true },
    };

    static defaultProps = {
        type: "secondary",
        titleActive: "",
        iconImgAttrs: {},
    };

    setup() {
        this.info = useActionInfo();
        const { state, operation } = useSelectableItemComponent(this.props.id);
        this.state = state;
        this.onClick = operation.commit;
        this.onPointerEnter = operation.preview;
        this.onPointerLeave = operation.revert;
    }

    get className() {
        let className = this.props.className || "";
        if (this.props.type) {
            className += ` btn-${this.props.type}`;
        }
        if (this.state.isActive) {
            className = `active ${className}`;
            if (this.props.classActive) {
                className += ` ${this.props.classActive}`;
            }
        }
        if (this.props.icon) {
            className += ` o-hb-btn-has-icon`;
        }
        if (this.props.iconImg) {
            className += ` o-hb-btn-has-img-icon`;
        }
        return className;
    }

    get iconClassName() {
        if (this.props.icon.startsWith("fa-")) {
            return `fa ${this.props.icon}`;
        } else if (this.props.icon.startsWith("oi-")) {
            return `oi ${this.props.icon}`;
        }
        return "";
    }
}

const ltrRtlSplittableProps = [
    "className",
    "actionParam",
    "actionValue",
    "classAction",
    "styleAction",
    "styleActionValue",
    "attributeAction",
    "attributeActionValue",
    "dataAttributeAction",
    "dataAttributeActionValue",
];

/**
 * Many options are BuilderButtonGroups with at least a "Left" and a "Right"
 * button, but their action actually depends on the start and end of the line
 * (e.g. `flex-row` vs `flex-row-reverse`). They need some logic to work across
 * all 4 possible combinations of LTR / RTL in the backend (builder) and the
 * frontend (iframe).
 *
 * The `BuilderButtonLtrRtl` is a helper component to share the logic.
 *
 * |                  | **Backend LTR** | **Backend RTL** |
 * | ---------------- | --------------- | --------------- |
 * | **Frontend LTR** |    LTR / LTR    |    LTR / RTL    |
 * | **Frontend RTL** |    RTL / LTR    |    RTL / RTL    |
 *
 * The place of the button (visually on the left or on the right) depends on the
 * _backend language_: in English, the 1st button is on the left, the 2nd is on
 * the right. In Arabic, the 1st button is on the right, the 2nd is on the left.
 * This is done by default (normal flow of the DOM). We then need to adapt each
 * button's label, icon, and action.
 *
 * **UNDERLYING LOGIC**:
 * - The label and icon of the button depend on the _backend direction_ (as
 * opposed to English, the 1st button in Arabic is on the right and should
 * always be labelled "right" with an arrow icon pointing right).
 * - The action of the button depends on whether both backend and frontend have
 * the same direction or not: if both are the same, the 1st button should have a
 * "start" action (in English: left = start, in Arabic: right = start). If both
 * are different, the 1st button should have an "end" action (backend in English
 * with a frontend in Arabic: left = end, right = start).
 *
 * **API**:
 * - All the "ltrRtlSplittableProps" can either take a single value if it
 * applies to both, or a `sameDir` key (when the backend and frontend directions
 * are the same) and a `diffDir` key (when they are different).
 * - The `label` prop takes a `left` and a `right` key for translatable strings,
 * applied as title / aria-label. By default, they are set on "Left" and
 * "Right". You can override the prop if you need a more specific text.
 * - The mandatory `position` prop takes either "start" or "end". It refers to
 * the position of the button in the UI, i.e. the normal flow of the document.
 * Always set the 1st `BuilderButtonLtrRtl` to "start" and the last one to "end"
 * - Note that icons are mirrored by default when the backend is RTL.
 *
 *  Examples:
 *
 *      <BuilderButtonGroup>
 *          <BuilderButtonLtrRtl position="'start'"
 *              classAction="{ sameDir: 'text-start', diffDir: 'text-end' }"
 *              icon="'fa-align-left'"/>
 *          <BuilderButtonLtrRtl position="'end'"
 *              classAction="{ sameDir: 'text-end', diffDir: 'text-start' }"
 *              icon="'fa-align-right'"/>
 *      </BuilderButtonGroup>
 *
 * Keep custom translatable strings in `t-set`, otherwise they won't be
 * translated:
 *
 *      <BuilderButtonGroup action="customAction">
 *          <t t-set="slideToLeft">Slide to left</t>
 *          <t t-set="slideToRight">Slide to right</t>
 *          <t t-set="label" t-value="{ left: slideToLeft, right: slideToRight }"/>
 *          <BuilderButtonLtrRtl position="'start'"
 *              label="label"
 *              actionParam="{ sameDir: 'start', diffDir: 'end' }"/>
 *          <BuilderButtonLtrRtl position="'end'"
 *              label="label"
 *              actionParam="{ sameDir: 'end', diffDir: 'start' }"/>
 *      </BuilderButtonGroup>
 */
export class BuilderButtonLtrRtl extends Component {
    static template = "html_builder.BuilderButtonLtrRtl";
    static components = { BuilderButton };
    static props = {
        position: { validate: (v) => ["start", "end"].includes(v) },
        label: { type: Object, optional: true },
        title: { type: String, optional: true },
        id: { type: String, optional: true },
        iconImg: { type: String, optional: true },
        icon: { type: String, optional: true },
        className: { type: Object, optional: true },
        actionParam: { type: Object, optional: true },
        actionValue: { type: Object, optional: true },
        classAction: { type: Object, optional: true },
        styleAction: { type: Object, optional: true },
        styleActionValue: { type: Object, optional: true },
        attributeAction: { type: Object, optional: true },
        attributeActionValue: { type: Object, optional: true },
        dataAttributeAction: { type: Object, optional: true },
        dataAttributeActionValue: { type: Object, optional: true },
        slots: { type: Object, optional: true },
    };

    static defaultProps = {
        label: { left: _t("Left"), right: _t("Right") },
        className: { sameDir: undefined, diffDir: undefined },
        actionParam: { sameDir: undefined, diffDir: undefined },
        actionValue: { sameDir: undefined, diffDir: undefined },
        classAction: { sameDir: undefined, diffDir: undefined },
        styleAction: { sameDir: undefined, diffDir: undefined },
        styleActionValue: { sameDir: undefined, diffDir: undefined },
        attributeAction: { sameDir: undefined, diffDir: undefined },
        attributeActionValue: { sameDir: undefined, diffDir: undefined },
        dataAttributeAction: { sameDir: undefined, diffDir: undefined },
        dataAttributeActionValue: { sameDir: undefined, diffDir: undefined },
    };

    setup() {
        this.langDir = useLanguageDirection();
        this.iconImgAttrs =
            this.langDir.backend === "ltr" ? {} : { style: "transform: scaleX(-1);" };

        for (const prop of ltrRtlSplittableProps) {
            if (
                this.props[prop] instanceof Object &&
                "sameDir" in this.props[prop] &&
                "diffDir" in this.props[prop]
            ) {
                this[prop] = this.props[prop];
            } else {
                this[prop] = { sameDir: this.props[prop], diffDir: this.props[prop] };
            }
        }
    }

    get title() {
        if ((this.langDir.backend === "ltr") === (this.props.position === "start")) {
            return this.props.label.left;
        }
        return this.props.label.right;
    }
}
