import { unique } from "@web/core/utils/arrays";
import { exprToBoolean } from "@web/core/utils/strings";
import { createElement, parseXML } from "@web/core/utils/xml";
import { useService } from "@web/core/utils/hooks";
import { Card } from "@web/views/card/card";
import { CARD_ATTRIBUTE } from "@web/views/card/card_arch_parser";
import { CardRenderer } from "@web/views/card/card_renderer";
import { useViewButtons } from "@web/views/view_button/view_button_hook";

import { Component, onWillStart, t, useProps } from "@odoo/owl";

export const BODY_ATTRIBUTE = "popover-body";
export const FOOTER_ATTRIBUTE = "popover-footer";
export const HEADER_ATTRIBUTE = "popover-header";

/**
 * Extracts the templates and direct field children from the given arch node.
 *
 * Example:
 * <popover>
 *     <field name="some_field"/>
 *     <templates>
 *         <t t-name="popover-header">...</t>
 *         <t t-name="popover-body">...</t>
 *         <t t-name="popover-footer">...</t>
 *     </templates>
 * </popover>
 *
 * @param {Element} node
 * @returns {{fields: string[], templates: Record<string, Element>}}
 */
export function extractTemplatesAndFields(node) {
    const fields = [];
    const templates = {};
    for (const childNode of node.children) {
        if (childNode.tagName === "field") {
            fields.push(childNode.getAttribute("name"));
        } else if (childNode.tagName === "templates") {
            for (const templateNode of childNode.children) {
                const name = templateNode.getAttribute("t-name");
                if (name) {
                    templates[name] = templateNode;
                }
            }
        }
    }
    return { fields, templates };
}

class CardPopoverRenderer extends CardRenderer {
    static template = "web.CardPopoverRenderer";
    static BODY_ATTRIBUTE = BODY_ATTRIBUTE;
    static FOOTER_ATTRIBUTE = FOOTER_ATTRIBUTE;
    static HEADER_ATTRIBUTE = HEADER_ATTRIBUTE;
}

class CardPopoverCard extends Card {
    static components = { ...Card.components, CardRenderer: CardPopoverRenderer };
    afterButtonClicked = useProps.static("afterButtonClicked", t.function());
    slots = useProps.static("slots", t.any());

    setup() {
        super.setup();
        useViewButtons(this.rootRef, {
            reload: () => this.afterButtonClicked(),
        });
    }

    get rendererProps() {
        return {
            ...super.rendererProps,
            slots: this.slots, // propagate defaultFooter slot
        };
    }
}

/**
 * Base component for the popovers used by views (calendar, gantt, map, ...)
 * to display a record as a "card" in a popover. Concrete popovers wrap this
 * component (composition, not inheritance).
 */
export class CardPopover extends Component {
    static template = "web.CardPopover";
    static components = { CardPopoverCard };

    props = useProps({
        close: t.function(),
        fields: t.object(),
        resModel: t.string(),
        resId: t.number(),
        getDefaultPopoverBody: t.function(),
        // optional for retro-compatibility reasons
        popoverNode: t.instanceOf(Element).optional(() => parseXML("<t/>")),
        readonly: t.boolean().optional(false),
        rootClass: t.string().optional(),
        context: t.object().optional(() => ({})),
        reloadOnClose: t.function().optional(() => () => {}),
        openRecord: t.function().optional(() => () => {}),
    });

    setup() {
        this.viewService = useService("view");

        onWillStart(async () => {
            const { xmlDoc, fields, displayDefaultFooter } = await this.buildCardPopover();
            this.cardXmlDoc = xmlDoc;
            this.cardFields = fields;
            this.displayDefaultFooter = displayDefaultFooter;
        });
    }

    get cardProps() {
        return {
            card: this.cardXmlDoc,
            context: this.props.context,
            fields: this.cardFields,
            resModel: this.props.resModel,
            resId: this.props.resId,
            readonly: this.props.readonly,
            afterButtonClicked: () => {
                this.props.reloadOnClose();
                this.props.close();
            },
            hooks: {
                onRecordSaved: this.props.reloadOnClose,
            },
        };
    }

    /**
     * Builds the "card" view arch used to render the CardPopoverCard,
     * merging the templates/fields declared inline in the `popover` prop
     * with those of an optional `card_id` view, and falling back on
     * `getDefaultPopoverBody`/`getDefaultPopoverHeader` when nothing was
     * provided.
     *
     * @returns {Promise<{xmlDoc: Element, fields: Object, displayDefaultFooter: boolean}>}
     */
    async buildCardPopover() {
        const popoverNode = this.props.popoverNode.cloneNode(true);
        const cardId = parseInt(popoverNode.getAttribute("card_id"), 10) || false;
        const popoverInfo = extractTemplatesAndFields(popoverNode);
        let allFields = this.props.fields;
        let fieldNames = popoverInfo.fields;
        let templates = popoverInfo.templates;

        // load the card if cardId is set and no popover-body is defined
        if (cardId && !(BODY_ATTRIBUTE in templates)) {
            const { fields, views } = await this.viewService.loadViews({
                resModel: this.props.resModel,
                views: [[cardId, "card"]],
                context: this.props.context,
            });
            allFields = { ...fields, ...allFields };
            const cardInfo = extractTemplatesAndFields(parseXML(views.card.arch));
            templates = { ...cardInfo.templates, ...templates };
            fieldNames = unique(fieldNames.concat(cardInfo.fields));
        }

        // the Card component expects the main template to be named "card"
        if (BODY_ATTRIBUTE in templates) {
            const bodyTemplate = templates[BODY_ATTRIBUTE];
            bodyTemplate.setAttribute("t-name", CARD_ATTRIBUTE);
            templates[CARD_ATTRIBUTE] = bodyTemplate;
            delete templates[BODY_ATTRIBUTE];
        }

        // generate default templates if not provided
        if (!templates[CARD_ATTRIBUTE]) {
            templates[CARD_ATTRIBUTE] = this.props.getDefaultPopoverBody();
            if (!templates[HEADER_ATTRIBUTE]) {
                const header = this.getDefaultPopoverHeader();
                if (header) {
                    templates[HEADER_ATTRIBUTE] = header;
                }
            }
        }

        // default footer
        const footer = templates[FOOTER_ATTRIBUTE];
        const displayDefaultFooter =
            !footer || // display default if no footer provided
            // or if attribute replace="0" has been set on the footer template
            (footer.hasAttribute("replace") && !exprToBoolean(footer.getAttribute("replace")));

        // generate a "card" view arch
        const cardXmlDoc = createElement("card");
        const templatesNode = createElement("templates");
        for (const fieldName of fieldNames) {
            templatesNode.appendChild(createElement("field", { name: fieldName }));
        }
        for (const template in templates) {
            templatesNode.appendChild(templates[template]);
        }
        cardXmlDoc.appendChild(templatesNode);
        return { xmlDoc: cardXmlDoc, fields: allFields, displayDefaultFooter };
    }

    /**
     * Returns the default popover header, showing the record's `display_name`.
     *
     * @returns {Element}
     */
    getDefaultPopoverHeader() {
        return parseXML(`<t t-name="${HEADER_ATTRIBUTE}"><field name="display_name"/></t>`);
    }
}
