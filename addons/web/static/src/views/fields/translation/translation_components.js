import {
    Component,
    xml,
    computed,
    signal,
    untrack,
    types,
    props,
    providePlugins,
    plugin,
} from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { Dialog } from "@web/core/dialog/dialog";
import { memoize } from "@web/core/utils/functions";
import { Record } from "@web/model/record";
import { makeActiveField } from "@web/model/relational_model/utils";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

import { TranslateModel } from "./translation_model";

function smoothStickyTop(stickyClass, ref) {
    let isScrolling = false;
    let oldScrollTop = 0;
    const initialScrollTop = 0;
    let lastScrollTop = 0;
    return () => {
        const el = ref();
        if (isScrolling || !el) {
            return;
        }
        isScrolling = true;
        browser.requestAnimationFrame(() => (isScrolling = false));

        const scrollTop = el.offsetParent.scrollTop;
        const delta = Math.round(scrollTop - oldScrollTop);

        if (scrollTop > initialScrollTop) {
            // Beneath initial position => sticky display
            el.classList.add(stickyClass);
            if (delta <= 0) {
                // Going up | not moving
                lastScrollTop = Math.min(0, lastScrollTop - delta);
            } else {
                // Going down
                lastScrollTop = Math.max(-el.offsetHeight, -el.offsetTop - delta);
            }
            el.style.top = `${lastScrollTop}px`;
        } else {
            // Above initial position => standard display
            el.classList.remove(stickyClass);
            lastScrollTop = 0;
        }
        oldScrollTop = scrollTop;
    };
}

const childrenLoopTemplate = xml`
<t t-foreach="node.childNodes" t-as="c" t-key="c_index">
    <t t-if="c.nodeType === 1" t-call="{{ this.nodeTemplate }}" node="c"/>
    <t t-if="c.nodeType === 3" ><t t-out="c.textContent" /></t>
</t>
`;

const translateNodeTemplate = xml`
<t t-set="parsed" t-value="this.parseNode(node)" />
<span class="d-block">
    <input class="d-inline ps-1 o-translate--translatable-block" t-att="parsed.attributes" t-att-value="parsed.value()" />
</span>
`;

const attributeTemplate = xml`
<span class="o-att">
    <span class="o-att-name" t-out="attribute[0]" />=
    <t t-set="attrToNode" t-value="this.parseAttrXML(attribute[1])" />
    <t t-if="attrToNode">
        <t t-call="${translateNodeTemplate}" node="attrToNode"/>
    </t>
    <t t-else="">
        "<span class="o-att-value" t-out="attribute[1]"/>"
    </t>
</span>
`;

const nodeTemplate = xml`
<t t-set="parsed" t-value="this.parseNode(node)" />
<li t-if="parsed.nodeMode === 'node'" class="text-nowrap">
    <span class="text-muted">
        <span class="o-tag-name">&lt;<t t-out="node.tagName.toLowerCase()" /> </span>
        <t t-foreach="node.getAttributeNames()" t-as="attname" t-key="attname" >
            <t t-call="${attributeTemplate}" attribute="[attname, node.getAttribute(attname)]"/>
        </t>
        <span>&gt;</span>
    </span>
    <ul class="o-node-list">
        <t t-call="${childrenLoopTemplate}" node="node"/>
    </ul>
</li>
<t t-elif="parsed.nodeMode === 'translationBlock'">
    <t t-call="${translateNodeTemplate}" />
</t>
<t t-else="">
    <t t-call="${childrenLoopTemplate}" />
</t>
`;

class LanguageButtons extends Component {
    static template = "web.translate.LanguageButtons";
    model = plugin(TranslateModel);
    languages = props.static(
        "languages",
        types.signal().optional(() => this.model.languages)
    );
    onChange = props.static(
        "onChange",
        types.function().optional(() => this.model.changeLang.bind(this.model))
    );
    languageEntries = computed(() => Object.entries(this.languages()));
}

export class TranslateXml extends Component {
    static template = "web.translate.TranslateXml";
    static components = { LanguageButtons };

    nodeTemplate = nodeTemplate;
    childrenLoopTemplate = childrenLoopTemplate;

    model = plugin(TranslateModel);
    rootRef = signal(null);
    langButtonsRef = signal(null);
    onScroll = smoothStickyTop("position-sticky", this.langButtonsRef);

    mimetype = computed(() =>
        this.model.field().type === "html" ? "text/html" : "application/xhtml+xml"
    );
    currentValue = computed(() =>
        this.parseXML(this.model.xmlValues()[this.model.currentLang()], this.mimetype())
    );
    nodeWeakMap = new WeakMap();

    parseXML = memoize((value, mimetype) => {
        const tree = new DOMParser().parseFromString(`<div>${value}</div>`, mimetype);
        if (tree instanceof HTMLDocument) {
            return tree.body;
        }
        return tree;
    });

    parseNode(node) {
        if (this.nodeWeakMap.has(node)) {
            return this.nodeWeakMap.get(node);
        }
        const parsed = {};
        this.nodeWeakMap.set(node, parsed);
        if (node.getAttribute("data-oe-translation-state")) {
            if (!node.querySelector("[data-oe-translation-state]")) {
                parsed.nodeMode = "translationBlock";
            }
        } else {
            parsed.nodeMode = "node";
        }
        if (parsed.nodeMode === "translationBlock") {
            const attributes = Object.fromEntries(
                node.getAttributeNames().map((attName) => [attName, node.getAttribute(attName)])
            );
            attributes["data-width"] = this.computeInputWidth(node.innerHTML || node.innerText);
            parsed.attributes = attributes;
            const translationKey = this.model.getTranslationKey(attributes);
            attributes["data-translation-key"] = translationKey;
            parsed.value = (lang) =>
                this.getHashChange(lang, translationKey) ?? (node.innerHTML || node.innerText);
        }
        return parsed;
    }

    getHashChange(lang, key) {
        // We want to store changes in the model to go back and forth between languages
        // But we don't want to trigger a render at each input
        // This is why we untrack the underlying reactive
        return untrack(() => this.model.getHashChange(lang, key));
    }

    computeInputWidth(value) {
        // See the stylesheet for this component
        // this will be cast as a value in `ch`
        return Math.max(value.length, 10);
    }

    onInput(ev) {
        const target = ev.target;
        if (target.hasAttribute("data-oe-translation-state")) {
            const key = target.getAttribute("data-translation-key");
            this.model.setHashChange(null, key, target.value);
            target.dataset.oeTranslationState = "translated";
            target.dataset.width = this.computeInputWidth(target.value);
        }
    }

    static translatableAttrRe = new RegExp("(<span.*>)(.*)(</span>)");
    parseAttrXML(string) {
        string = string?.trim();
        if (string?.startsWith("<span data-oe-model=")) {
            const matched = string.match(this.constructor.translatableAttrRe);
            if (matched.length === 4) {
                const text = matched[2];
                const dummy = this.parseXML(matched[1] + matched[3], "text/html").firstElementChild
                    .firstElementChild;
                dummy.innerText = text;
                return dummy;
            }
        }
    }
}

export class TranslateText extends Component {
    static template = "web.translate.TranslateText";
    static components = { Dropdown, DropdownItem };
    model = plugin(TranslateModel);

    get inputTag() {
        return (this.model.fieldType ?? "text") === "text" ? "textarea" : "input";
    }

    onChange(ev) {
        const target = ev.target;
        const lang = target.id;
        const value = target.value;
        this.model.setValue(lang, value);
    }
}

export class TranslateHTML extends TranslateText {
    static template = "web.translate.TranslateHTML";
    static components = { ...TranslateText.components, Record, LanguageButtons };

    propsHtmlField = props({
        fieldComponentClass: types.constructor(Component).optional(),
        fieldComponentProps: types.object().optional(),
        getFakeRecordInfos: types.function().optional(),
    });

    fakeRecordProps = computed(() => this._getfakeRecordProps());

    availableLanguages = computed(() =>
        Object.fromEntries(
            Object.entries(this.model.languages()).filter((e) => e[0] !== this.model.userLang)
        )
    );

    _getfakeRecordProps() {
        const { fields, activeFields, values, currentField } =
            this.propsHtmlField.getFakeRecordInfos?.() ?? {
                fields: {},
                activeFields: {},
                values: {},
                currentField: { type: "html" },
            };
        for (const lang in this.model.languages()) {
            fields[lang] = { ...currentField, translate: false, name: lang };
            activeFields[lang] = makeActiveField();
            values[lang] = this.model.getValue(lang);
        }

        return {
            fields,
            resModel: "dummy",
            resId: 1,
            mode: "edit",
            activeFields,
            hooks: {
                onRecordChanged: (record, changes) => {
                    for (const [fname, value] of Object.entries(changes)) {
                        this.model.setValue(fname, value);
                    }
                },
            },
            values,
        };
    }

    fieldComponentClass = computed(
        () =>
            this.propsHtmlField.fieldComponentClass ||
            registry.category("fields").get("html")?.component
    );

    fieldComponentProps = computed(() => ({
        ...this.propsHtmlField.fieldComponentProps,
        ...this.defaultComponentProps(this.fieldComponentClass),
    }));

    defaultComponentProps(Component) {
        return { codeview: true };
    }
}

export class TranslationDialog extends Component {
    static template = "web.translate.TranslationDialog";
    static components = {
        TranslateText,
        TranslateHTML,
        TranslateXml,
        Dialog,
    };

    props = props({
        title: types.signal().optional(),
        close: types.function().optional(),
        fieldComponentClass: types.constructor(Component).optional(),
        fieldComponentProps: types.object().optional(),
        getFakeRecordInfos: types.function().optional(),
        Plugins: types.array().optional(),
        config: types.object().optional(),
        onSaved: types.signal(types.function()).optional(),
    });

    dialogTitle = computed(() => this.props.title?.() ?? this.model.getTitle() ?? _t("Translate"));
    dialogSize = computed(() => {
        switch (this.model.translateMode()) {
            case "html":
                return "xl";
            case "xml":
                return "lg";
            default:
                return "md";
        }
    });

    setup() {
        providePlugins(this.props.Plugins ?? [TranslateModel], this.props.config);
        this.model = plugin(TranslateModel);
        if (this.props.onSaved) {
            this.model.on_saved.use(this.props.onSaved());
        }
        if (this.props.close) {
            this.model.on_saved.use(this.props.close);
        }
    }
}
