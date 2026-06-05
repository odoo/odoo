import { Component, signal } from "@odoo/owl";
import { useNavigation } from "@web/core/navigation/navigation";

export class SuggestionList extends Component {
    static props = {
        state: Object,
        onSelect: Function,
        overlay: Object,
    };
    static template = "html_editor.SuggestionList";

    suggestionListRef = signal(null);

    setup() {
        this.navigation = useNavigation(this.suggestionListRef, {
            isNavigationAvailable: () => this.props.overlay.isOpen,
            shouldFocusFirstItem: true,
            hotkeys: {
                "shift+Enter": {
                    bypassEditableProtection: true,
                    isAvailable: () => true,
                    callback: (navigator) => {
                        navigator.activeItem.select();
                    },
                },
            },
        });
    }

    onClick(item) {
        this.props.onSelect(item);
    }
}
