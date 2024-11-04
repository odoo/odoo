import { registry } from "@web/core/registry";
import { BoardController } from "./board_controller";
import { visitXML } from "@web/core/utils/xml";
import { Domain } from "@web/core/domain";
export class BoardArchParser {
    parse(arch, customViewId) {
        let nextId = 1;
        const archInfo = {
            title: null,
            layout: null,
            colNumber: 0,
            isEmpty: true,
            columns: [{ actions: [] }, { actions: [] }, { actions: [] }],
            customViewId,
        };
        let currentIndex = -1;

        visitXML(arch, (node) => {
            switch (node.tagName) {
                case "form":
                    archInfo.title = node.getAttribute("string");
                    break;
                case "board":
                    archInfo.layout = node.getAttribute("style");
                    archInfo.colNumber = archInfo.layout.split("-").length;
                    break;
                case "column":
                    currentIndex++;
                    break;
                case "action": {
                    archInfo.isEmpty = false;
                    const isFolded = Boolean(
                        node.hasAttribute("fold") ? parseInt(node.getAttribute("fold"), 10) : 0
                    );
                    const action = {
                        id: nextId++,
                        title: node.getAttribute("string"),
                        actionId: parseInt(node.getAttribute("name"), 10),
                        viewMode: node.getAttribute("view_mode"),
                        context: node.getAttribute("context"),
                        isFolded,
                    };
                    if (node.hasAttribute("domain")) {
                        const domain = node.getAttribute("domain");
                        action.domain = new Domain(domain).toList();
                        // so it can be serialized when reexporting board xml
                        action.domain.toString = () => node.getAttribute("domain");
                    }
                    archInfo.columns[currentIndex].actions.push(action);
                    break;
                }
            }
        });
        return archInfo;
    }
}

export const boardView = {
    type: "form",
    Controller: BoardController,

    props: (genericProps, view) => {
        const { arch, info } = genericProps;
        const board = new BoardArchParser().parse(arch, info.customViewId);
        return {
            ...genericProps,
            className: "o_dashboard",
            board,
        };
    },
};

registry.category("views").add("board", boardView);
