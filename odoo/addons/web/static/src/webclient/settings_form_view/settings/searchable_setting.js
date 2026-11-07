/** @odoo-module **/

import { escapeRegExp } from "@web/core/utils/strings";
import { Setting } from "@web/views/form/setting/setting";
import { onMounted, useRef, useState } from "@odoo/owl";
import { FormLabelHighlightText } from "../highlight_text/form_label_highlight_text";
import { HighlightText } from "../highlight_text/highlight_text";

export class SearchableSetting extends Setting {
    setup() {
        this.settingRef = useRef("setting");
        this.state = useState({
            search: this.env.searchState,
            showAllContainer: this.env.showAllContainer,
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
        });
    }

    get classNames() {
        const classNames = super.classNames;
        classNames.o_searchable_setting = Boolean(this.labels.length);
        return classNames;
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
SearchableSetting.template = "web.SearchableSetting";
SearchableSetting.components = {
    ...Setting.components,
    FormLabel: FormLabelHighlightText,
    HighlightText,
};
