import { HtmlField, htmlField, htmlFieldProps } from "@html_editor/fields/html_field";
import { registry } from "@web/core/registry";
import { ColumnPlugin } from "@html_editor/main/column_plugin";
import { MoveNodePlugin } from "@html_editor/main/movenode_plugin";
import { user } from "@web/core/user";
import { t, useProps, useScope } from "@odoo/owl";
import { useEmailHtmlConverter, useSavePendingImage } from "@mail/convert_inline/hooks";
import { childNodes } from "@html_editor/utils/dom_traversal";

export class HtmlMailField extends HtmlField {
    props = useProps({
        ...htmlFieldProps,
        disableMoveNodePlugin: t.boolean().optional(),
    });

    setup() {
        super.setup();
        this.scope = useScope();
        this.converter = useEmailHtmlConverter({
            bundles: ["mail.assets_convert_inline"],
        });
        this._savePendingImages = useSavePendingImage({
            getLastChangeId: () => this.lastChangeId,
            setLastChangeId: (id) => (this.lastChangeId = id),
        });
    }

    /**
     * @see useSavePendingImage
     * @override
     */
    async savePendingImages(content) {
        await this._savePendingImages({ content, editor: this.editor });
    }

    /**
     * Convert editor content to mail compliant html
     * @override
     */
    async getEditorContent() {
        const content = await super.getEditorContent();
        const fragment = document.createDocumentFragment();
        fragment.append(...childNodes(content.cloneNode(true)));
        const template = await this.converter.convertToEmailHtml(fragment, {
            debug: this.env.debug,
        });
        if (template) {
            content.replaceChildren(template.content);
        }
        return content;
    }

    getConfig() {
        const config = super.getConfig();
        config.dropImageAsAttachment = false;
        config.defaultLinkAttributes = { target: "_blank", rel: "noreferrer noopener" };
        const disabledPlugins = new Set([ColumnPlugin]);
        if (this.props.disableMoveNodePlugin) {
            disabledPlugins.add(MoveNodePlugin);
        }
        config.Plugins = [
            ...new Set(config.Plugins.filter((plugin) => !disabledPlugins.has(plugin))).union(
                new Set(registry.category("mail-core-plugins").getAll())
            ),
        ];
        config.measureReference = this.converter.measureReference;
        config.dynamicFieldFilter = this.dynamicFieldFilter.bind(this);
        config.dynamicFieldPreprocess = ({ resModel }) => this.loadAllowedExpressions(resModel);
        config.dynamicFieldPostprocess = this.dynamicFieldPostprocess.bind(this);
        return config;
    }

    dynamicFieldFilter(fieldDef, path) {
        const fullPath = `object${path ? `.${path}` : ""}.${fieldDef.name}`;
        if (!this.isTemplateEditor && !this.allowedQwebExpressions.includes(fullPath)) {
            return false;
        }
        return !["one2many", "boolean", "many2many"].includes(fieldDef.type) && fieldDef.searchable;
    }

    async dynamicFieldPostprocess({ path, label, fieldInfo, resModel, element }) {
        if (fieldInfo.type !== "datetime") {
            return;
        }

        const partnerFields = await this.ormService.call(resModel, "mail_get_partner_fields", [[]]);

        let out = partnerFields.length
            ? `format_datetime(${path}, tz=object.${partnerFields[0]}.tz)`
            : `format_datetime(${path})`;

        if (label) {
            const safeDefaultValue = label.replace(/'/g, "\\'");
            out += ` or '${safeDefaultValue}'`;
        }

        element.setAttribute("t-out", out);
        element.removeAttribute("t-field");
    }

    async loadAllowedExpressions(resModel) {
        const getAllowedQwebExpressions = this.env.services["allowed_qweb_expressions"];
        [this.isTemplateEditor, this.allowedQwebExpressions] = await Promise.all([
            user.hasGroup("mail.group_mail_template_editor"),
            getAllowedQwebExpressions(resModel),
        ]);
    }
}

export const htmlMailField = {
    ...htmlField,
    component: HtmlMailField,
    additionalClasses: ["o_field_html"],
    extractProps({ attrs, options }, dynamicInfo) {
        const props = htmlField.extractProps({ attrs, options }, dynamicInfo);
        if ("no_move_node_plugin" in options && Boolean(options.no_move_node_plugin)) {
            props.disableMoveNodePlugin = true;
        }
        props.embeddedComponents = false;
        return props;
    },
};

registry.category("fields").add("html_mail", htmlMailField);
