import { useState } from "@web/owl2/utils";
import { onMounted } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { normalize } from "@web/core/l10n/utils";
import { Setting } from "@web/views/form/setting/setting";
import { FormLabelHighlightText } from "../highlight_text/form_label_highlight_text";
import { HighlightText } from "../highlight_text/highlight_text";

export class SearchableSetting extends Setting {
    static template = "web.SearchableSetting";
    static components = {
        ...Setting.components,
        FormLabel: FormLabelHighlightText,
        HighlightText,
    };
    setup() {
        this.state = useState({
            search: this.env.searchState,
            showAllContainer: this.env.showAllContainer,
            highlightClass: {},
        });
        this.labels = [this.labelString, this.props.title].filter(Boolean);
        super.setup();
        onMounted(() => {
            if (browser.location.hash.substring(1) === this.props.id) {
                this.state.highlightClass = { o_setting_highlight: true };
                setTimeout(() => (this.state.highlightClass = {}), 5000);
            }
        });
    }

    get classNames() {
        const classNames = super.classNames;
        classNames.o_searchable_setting = Boolean(this.labels.length);
        return { ...classNames, ...this.state.highlightClass };
    }

    visible() {
        if (!this.state.search.value) {
            return true;
        }
        if (this.state.showAllContainer.showAllContainer) {
            return true;
        }
        if (normalize(this.labels.join()).includes(this.state.search.value)) {
            return true;
        }
        return false;
    }
}
