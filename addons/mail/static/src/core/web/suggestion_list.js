import { Component, onPatched, useExternalListener, useRef } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { ImStatus } from "../common/im_status";

export class SuggestionList extends Component {
    static template = "mail.SuggestionList";
    static components = { ImStatus };
    static props = {
        document: { validate: (doc) => doc.constructor.name === "HTMLDocument" },
        close: Function,
        state: Object,
        activateSuggestion: Function,
        applySuggestion: Function,
    };

    setup() {
        const ref = useRef("root");
        onPatched(() => {
            const activeCommand = ref.el?.querySelector(".o-mail-Composer-suggestion.active");
            if (activeCommand) {
                activeCommand.scrollIntoView({ block: "nearest", inline: "nearest" });
            }
        });
        this.mouseSelectionActive = false;
        this.ui = useService("ui");
        useExternalListener(this.props.document, "mousemove", () => {
            this.mouseSelectionActive = true;
        });
    }

    get template() {
        switch (this.props.state.type) {
            case "ChannelCommand":
                return "mail.SuggestionList.Command";
            case "Emoji":
                return "mail.SuggestionList.Emoji";
            case "Thread":
                return "mail.SuggestionList.Thread";
            case "CannedResponse":
                return "mail.SuggestionList.CannedResponse";
            case "Partner":
                return "mail.SuggestionList.Partner";
            default:
                return "";
        }
    }

    get suggestions() {
        return this.props.state.suggestions;
    }

    get currentIndex() {
        return this.props.state.currentIndex;
    }

    onScroll() {
        this.mouseSelectionActive = false;
    }

    onMouseEnter(index) {
        if (this.mouseSelectionActive) {
            this.props.activateSuggestion(index);
        }
    }
}
