import { Component, onPatched, signal, t, useEffect, useListener, useProps } from "@odoo/owl";

/**
 * @todo @phoenix i think that most of the "control" code in this component
 * should move to the powerbox plugin instead. This would probably be more robust
 */
export class Powerbox extends Component {
    static template = "html_editor.Powerbox";
    props = useProps({
        document: t.customValidator(t.any(), (doc) => doc.constructor.name === "HTMLDocument"),
        close: t.function(),
        state: t.object(),
        activateCommand: t.function(),
        applyCommand: t.function(),
    });

    setup() {
        this.root = signal.ref();

        onPatched(() => {
            const activeCommand = this.root().querySelector(".o-we-command.active");
            if (activeCommand) {
                activeCommand.scrollIntoView({ block: "nearest", inline: "nearest" });
            }
        });

        this.mouseSelectionActive = false;
        const onMouseMove = () => (this.mouseSelectionActive = true);
        useListener(this.props.document, "mousemove", onMouseMove);

        // If necessary attach the same listener on the document on which
        // the powerbox is mounted, serving the same purpose:
        // do not trigger re-renderings when we are scrolling the powerbox
        useEffect(() => {
            const doc = this.root()?.ownerDocument;
            if (doc && doc !== this.props.document) {
                doc.addEventListener("mousemove", onMouseMove);
                return () => doc.removeEventListener("mousemove", onMouseMove);
            }
        });
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
