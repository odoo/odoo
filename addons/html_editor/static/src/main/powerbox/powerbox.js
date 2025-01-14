import { Component, onPatched, useEffect, useExternalListener, useRef } from "@odoo/owl";

/**
 * @todo @phoenix i think that most of the "control" code in this component
 * should move to the powerbox plugin instead. This would probably be more robust
 */
export class Powerbox extends Component {
    static template = "html_editor.Powerbox";
    static props = {
        document: { validate: (doc) => doc.constructor.name === "HTMLDocument" },
        close: Function,
        state: Object,
        activateCommand: Function,
        applyCommand: Function,
    };

    setup() {
        const ref = useRef("root");

        onPatched(() => {
            const activeCommand = ref.el.querySelector(".o-we-command.active");
            if (activeCommand) {
                activeCommand.scrollIntoView({ block: "nearest", inline: "nearest" });
            }
        });

        this.mouseSelectionActive = false;
        const onMouseMove = () => (this.mouseSelectionActive = true);
        useExternalListener(this.props.document, "mousemove", onMouseMove);

        // If necessary attach the same listener on the document on which
        // the powerbox is mounted, serving the same purpose:
        // do not trigger re-renderings when we are scrolling the powerbox
        useEffect(
            (ownDoc, propsDoc) => {
                if (ownDoc && propsDoc && ownDoc !== propsDoc) {
                    ownDoc.addEventListener("mousemove", onMouseMove);
                    return () => ownDoc.removeEventListener("mousemove", onMouseMove);
                }
            },
            () => [ref.el?.ownerDocument, this.props.document]
        );
    }

    get commands() {
        return this.props.state.commands;
    }

    get currentIndex() {
        return this.props.state.currentIndex;
    }

    get showCategories() {
        return this.props.state.showCategories;
    }

    onScroll() {
        this.mouseSelectionActive = false;
    }

    onMouseEnter(index) {
        if (this.mouseSelectionActive) {
            this.props.activateCommand(index);
        }
    }
}
