import { escapeRegExp } from "@web/core/utils/strings";
import { Setting } from "@web/views/form/setting/setting";
import { onMounted, useRef, useState } from "@odoo/owl";
import { FormLabelHighlightText } from "../highlight_text/form_label_highlight_text";
import { HighlightText } from "../highlight_text/highlight_text";
import { browser } from "@web/core/browser/browser";

export class SearchableSetting extends Setting {
    static template = "web.SearchableSetting";
    static components = {
        ...Setting.components,
        FormLabel: FormLabelHighlightText,
        HighlightText,
    };
    setup() {
        this.settingRef = useRef("setting");
        this.state = useState({
            search: this.env.searchState,
            showAllContainer: this.env.showAllContainer,
            highlightClass: {},
        });
        this.labels = [];
        this.labels.push(this.labelString, this.props.help);
        super.setup();
        onMounted(() => {
            if (this.settingRef.el) {
                const searchableTexts = this.settingRef.el.querySelectorAll("span[searchableText]");
                searchableTexts.forEach((st) => {
                    this.labels.push(st.getAttribute("searchableText"));
                });
            }
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
        const regexp = new RegExp(escapeRegExp(this.state.search.value), "i");
        if (regexp.test(this.labels.join())) {
            return true;
        }
        return false;
    }
}
