import { Component, signal, t, useProps } from "@odoo/owl";
import { useNavigation } from "@web/core/navigation/navigation";

export class SuggestionList extends Component {
    props = useProps({
        state: t.object(),
        onSelect: t.function(),
        overlay: t.object(),
    });
    static template = "html_editor.SuggestionList";

    suggestionListRef = signal.ref();

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
