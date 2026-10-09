import { visitXML } from "@web/core/utils/xml";
import { Widget } from "@web/views/widgets/widget";

/**
 * Parses the <help> node inlined by the server in a view arch when its root
 * node has a `help_id` attribute (it references a view of type "help").
 */
export class HelpArchParser {
    parse(xmlDoc) {
        const widgetNodes = {};
        let nextWidgetId = 0;
        visitXML(xmlDoc, (node) => {
            if (node.tagName === "widget") {
                const widgetId = `widget_${nextWidgetId++}`;
                widgetNodes[widgetId] = Widget.parseWidgetNode(node);
                node.setAttribute("widget_id", widgetId);
            }
        });
        // name of the model method returning the data of the help (see `data_method`)
        const dataMethod = xmlDoc.getAttribute("data_method");
        return { xmlDoc, widgetNodes, dataMethod };
    }
}

/**
 * Removes the <help> node (if any) from the given view arch, and returns its
 * parsed version. It must be removed before parsing the arch, as the view arch
 * parsers aren't aware of it (e.g. its buttons must not be considered as list
 * buttons).
 *
 * @param {Element} archXmlDoc
 * @returns {Object | null}
 */
export function extractHelpArchInfo(archXmlDoc) {
    const helpNode = [...archXmlDoc.children].find((node) => node.tagName === "help");
    if (!helpNode) {
        return null;
    }
    helpNode.remove();
    return new HelpArchParser().parse(helpNode);
}
