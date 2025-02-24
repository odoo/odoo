import { Component, onPatched, useExternalListener, useRef } from "@odoo/owl";
import { ImStatus } from "./im_status";
import { mailSuggestionsRegistry } from "./suggestion_service";

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
            const activeCommand = ref.el.querySelector(".o-mail-Suggestion.active");
            if (activeCommand) {
                activeCommand.scrollIntoView({ block: "nearest", inline: "nearest" });
            }
        });

        this.mouseSelectionActive = false;
        this.mailSuggestionsRegistry = mailSuggestionsRegistry;
        useExternalListener(this.props.document, "mousemove", () => {
            this.mouseSelectionActive = true;
        });
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
