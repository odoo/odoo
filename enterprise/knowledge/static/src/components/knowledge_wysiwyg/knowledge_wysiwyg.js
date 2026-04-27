import { Wysiwyg } from "@html_editor/wysiwyg";
import { isEmptyBlock } from "@html_editor/utils/dom_info";
import { WysiwygArticleHelper } from "@knowledge/components/wysiwyg_article_helper/wysiwyg_article_helper";
import { useState } from "@odoo/owl";

export class KnowledgeWysiwyg extends Wysiwyg {
    static template = "knowledge.KnowledgeWysiwyg";
    static components = {
        ...Wysiwyg.components,
        WysiwygArticleHelper,
    };

    setup() {
        super.setup();
        this.articleHelperState = useState({
            isVisible: false,
        });
    }

    /** @override */
    getEditorConfig() {
        const config = super.getEditorConfig();
        return {
            ...config,
            onChange: () => {
                this.articleHelperState.isVisible = isEmptyBlock(this.editor.editable);
                config.onChange?.();
            },
            onEditorReady: () => {
                this.articleHelperState.isVisible = isEmptyBlock(this.editor.editable);
            },
        };
    }
}
