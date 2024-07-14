/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { Component, onWillStart, useEffect, useRef, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { groupBy } from "@web/core/utils/arrays";
import { HtmlField } from "@web_editor/js/backend/html_field";
import { Record } from "@web/model/record";
import { useService } from "@web/core/utils/hooks";


/**
 * This component will display an article template picker. The user will be able
 * to preview the article templates and select the one they want.
 */
export class ArticleTemplatePickerDialog extends Component {
    static template = "knowledge.ArticleTemplatePickerDialog";
    static components = {
        Dialog,
        Record,
        HtmlField
    };
    static props = {
        onLoadTemplate: { type: Function },
        close: { type: Function },
    };
    /**
     * @override
     */
    setup() {
        super.setup();
        this.size = "fs";
        this.title = _t("Select a Template");
        this.orm = useService("orm");
        this.scrollView = useRef("scroll-view");
        this.state = useState({});

        onWillStart(async () => {
            const templates = await this.orm.searchRead(
                "knowledge.article",
                [
                    ["is_template", "=", true],
                    ["parent_id", "=", false]
                ],
                [
                    "id",
                    "icon",
                    "template_name",
                    "template_category_id",
                    "template_category_sequence",
                    "template_sequence",
                ],
                {}
            );
            const groups = groupBy(templates, template => template["template_category_id"][0]);
            this.groups = Object.values(groups).sort((a, b) => {
                return a[0]["template_category_sequence"] > b[0]["template_category_sequence"];
            }).map(group => group.sort((a, b) => {
                return a["template_sequence"] > b["template_sequence"];
            }));
            if (this.groups.length > 0) {
                this.state.resId = this.groups[0][0].id;
            }
        });

        useEffect(() => {
            const { el } = this.scrollView;
            if (el) {
                el.style.visibility = "visible";
            }
        }, () => [this.state.resId]);
    }

    /**
     * @param {integer} articleTemplateId
     */
    async onSelectTemplate(articleTemplateId) {
        const { el } = this.scrollView;
        el.scrollTop = 0;
        if (articleTemplateId !== this.state.resId) {
            el.style.visibility = "hidden";
            this.state.resId = articleTemplateId;
        }
    }

    async onLoadTemplate() {
        this.props.onLoadTemplate(this.state.resId);
        this.props.close();
    }

    /**
     * @param {Record} record
     * @returns {Object}
     */
    getHtmlFieldProps(record) {
        return {
            record,
            readonly: true,
            name: "template_preview",
            wysiwygOptions: {},
        };
    }

    /**
     * @returns {Array[String]}
     */
    get articleTemplateFieldNames() {
        return [
            "cover_image_url",
            "icon",
            "id",
            "parent_id",
            "template_name",
            "template_preview",
            "template_description",
        ];
    }
}
