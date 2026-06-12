import { registry } from "@web/core/registry";
import { Plugin } from "../plugin";
import { withSequence } from "@html_editor/utils/resource";
import { Rules } from "../core/rules_models";
import { MainTableLayout, MainTableWrapper } from "./main_table_models";
import { StyleInfo } from "../core/style_models";
import { DEFAULT_SPACING_SEQUENCE } from "./spacing_plugin";

export class MainTableStrategyPlugin extends Plugin {
    static id = "mainTableStrategy";
    static dependencies = [
        "contextStyle",
        "filterContent",
        "measurementSnapshot",
        "rules",
        "spacing",
        "style",
        "referenceNode",
    ];
    resources = {
        // Sequence 1 is used so that this strategy is applied before e.g. the table strategy,
        // which would also match but is less relevant.
        element_layout_analysis_processors: withSequence(1, this.analyzeElementLayout.bind(this)),
        merge_layout_overrides: this.mergeNeutralReference.bind(this),
        on_reference_content_loaded_handlers: this.identifyLayout.bind(this),
        refine_layout_processors: withSequence(
            DEFAULT_SPACING_SEQUENCE - 1,
            this.discardMarginInfo.bind(this)
        ),
    };

    setup() {
        this.bodyGlobalStyleRules = new Rules();
        this.layoutRulesByRef = {
            root: new Rules(),
        };
        this.wrapperRulesByRef = {
            root: new Rules(),
        };
        this.provideLayoutStyleRules();
        this.provideWrapperStyleRules();
        this.provideBodyGlobalStyleRules();
    }

    mergeNeutralReference({ parentEmailNode, layout }) {
        if (
            parentEmailNode.referenceNodes.length !== 1 ||
            parentEmailNode.referenceNodes.at(0) !== this.config.reference
        ) {
            return;
        }
        if (parentEmailNode.layout.isNeutral()) {
            parentEmailNode.layout = layout;
            return true;
        }
    }

    discardMarginInfo(layout, { emailNode }) {
        if (emailNode.analysis.facts.isMainTable) {
            // Margin is already included in the main table layout, no need
            // for an extra wrapper
            emailNode.analysis.facts.desktopMarginStyleInfo = new StyleInfo();
        }
    }

    provideBodyGlobalStyleRules() {
        const globalRules = this.bodyGlobalStyleRules.forPlugin(MainTableStrategyPlugin.id);
        globalRules.allow("direction");
    }

    provideLayoutStyleRules() {
        const root = this.layoutRulesByRef.root.forPlugin(MainTableStrategyPlugin.id);
        root.allow("background-color", {
            when: ({ referenceNode }) => referenceNode.matches?.(".o_layout:not(.o_basic_theme)"),
        });
    }

    provideWrapperStyleRules() {
        const root = this.wrapperRulesByRef.root.forPlugin(MainTableStrategyPlugin.id);
        root.allow("max-width");
        root.allow(/^margin(-.*)?$/);
    }

    /**
     * Return a copy of the body styleInfo filtered with its own rules.
     */
    getBodyGlobalStyleInfo() {
        return this.filterStyleInfo(
            this.getRawStyleInfo(this.config.referenceDocument.body),
            this.config.referenceDocument.body,
            this.bodyGlobalStyleRules
        );
    }

    identifyLayout() {
        this.layout = this.config.reference.querySelector(".o_layout");
    }

    /**
     * TODO EGGMAIL: mutually exclusive identities? Does having this layout
     * prevent another plugin from claiming another layout? To think about.
     * evaluate withSequence
     */
    analyzeElementLayout(objectToProcess, { referenceNode }) {
        const { analysis } = objectToProcess;
        let isMainTable = this.detectMainTableLayout(referenceNode);
        let layout;
        if (isMainTable) {
            layout = this.buildMainTableLayout(
                referenceNode,
                MainTableLayout,
                this.layoutRulesByRef
            );
            analysis.facts.isMainTableLayout = true;
            analysis.parsingFacts.canParentMerge = this.config.reference !== referenceNode;
        } else if ((isMainTable = this.detectMainTableWrapper(referenceNode))) {
            layout = this.buildMainTableLayout(
                referenceNode,
                MainTableWrapper,
                this.wrapperRulesByRef
            );
            analysis.facts.isMainTableWrapper = true;
            analysis.parsingFacts.canParentMerge = false;
        }
        if (isMainTable) {
            analysis.facts.isMainTable = true;
            analysis.parsingFacts.canMerge = false;
            layout.pluginIds.add(MainTableStrategyPlugin.id);
            return { layout, analysis };
        }
    }

    buildMainTableLayout(referenceNode, MainTableModel, rulesByRef) {
        const refs = Object.fromEntries(
            Object.entries(rulesByRef).map(([ref, rules]) => [
                ref,
                {
                    style: this.filterStyleInfo(
                        this.getRawStyleInfo(referenceNode),
                        referenceNode,
                        rules
                    ),
                },
            ])
        );
        if (rulesByRef === this.layoutRulesByRef) {
            refs.root ??= {};
            const rootStyle = refs.root.style ?? {};
            refs.root.style = this.getBodyGlobalStyleInfo().merge(StyleInfo.from(rootStyle));
        }
        refs.td ??= {};
        const tdStyle = refs.td.style ?? {};
        refs.td.style = this.getContextStyleInfo(this.config.referenceDocument.body).merge(
            StyleInfo.from(tdStyle)
        );
        return new MainTableModel({ refs });
    }

    detectMainTableLayout(referenceNode) {
        if (this.layout) {
            return referenceNode === this.layout;
        } else {
            return referenceNode === this.config.reference;
        }
    }

    detectMainTableWrapper(referenceNode) {
        return referenceNode.matches?.(".o_mail_wrapper");
    }
}

registry
    .category("mail-html-conversion-main-plugins")
    .add(MainTableStrategyPlugin.id, MainTableStrategyPlugin);
