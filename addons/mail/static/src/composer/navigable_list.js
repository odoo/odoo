/* @odoo-module **/

import { useService } from "@web/core/utils/hooks";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";
import { usePosition } from "@web/core/position_hook";
import { ImStatus } from "../discuss/im_status"; // Used in composer suggestion template
import {
    Component,
    onMounted,
    onPatched,
    useEffect,
    useExternalListener,
    useRef,
    useState,
} from "@odoo/owl";
import { markEventHandled } from "../utils/misc";

export class NavigableList extends Component {
    static components = { ImStatus };
    static template = "mail.NavigableList";
    static props = {
        anchorRef: {},
        class: { type: String, optional: true },
        onSelect: { type: Function },
        options: { type: [Array, Promise] },
        optionTemplate: { type: String, optional: true },
        placeholder: { type: String, optional: true },
        position: { type: String, optional: true },
    };
    static defaultProps = { position: "bottom" };

    setup() {
        this.rootRef = useRef("root");
        this.state = useState({
            activeOption: null,
            isLoading: false,
            open: false,
            options: [],
        });
        this.hotkey = useService("hotkey");
        this.hotkeysToRemove = [];

        useExternalListener(window, "keydown", this.onKeydown, true);
        // position and size
        usePosition(() => this.props.anchorRef, {
            popper: "root",
            position: this.props.position,
        });
        useEffect(
            () => {
                this.open();
            },
            () => [this.props]
        );
        onMounted(() => {
            this.resizeObserver = new ResizeObserver(() => {
                const { width } = this.props.anchorRef.getBoundingClientRect();
                if (this.rootRef && this.rootRef.el) {
                    this.rootRef.el.style.width = width + "px";
                }
            });
        });
        onPatched(() => {
            if (this.props.anchorRef) {
                this.resizeObserver.observe(this.props.anchorRef);
            }
        });
    }

    get show() {
        return Boolean(this.state.open && (this.state.isLoading || this.state.options.length));
    }

    open() {
        this.load().then(() => {
            this.state.open = true;
            this.navigate("first");
        });
    }

    close() {
        this.state.open = false;
        this.state.activeOption = null;
    }

    async load() {
        this.state.options = [];
        const makeOption = (opt) => {
            return Object.assign(Object.create(opt), {
                id: this.state.options.length,
            });
        };
        if (this.props.options instanceof Promise) {
            this.state.isLoading = true;
            return this.props.options.then((opts) => {
                opts.forEach((opt) => this.state.options.push(makeOption(opt)));
                this.state.isLoading = false;
            });
        }
        if (this.props.options instanceof Array) {
            if (this.props.options.length === 0) {
                return;
            }
            this.props.options.forEach((opt) => this.state.options.push(makeOption(opt)));
        }
    }

    isActiveOption(option) {
        return this.state.activeOption?.id === option.id;
    }

    selectOption(ev, option, params = {}) {
        if (option.unselectable) {
            this.close();
            return;
        }
        this.props.onSelect(ev, option, {
            ...params,
        });
        this.close();
    }

    navigate(direction) {
        const activeOptionId = this.state.activeOption ? this.state.activeOption.id : -1;
        let targetId = undefined;
        switch (direction) {
            case "first":
                targetId = 0;
                break;
            case "last":
                targetId = this.state.options.length - 1;
                break;
            case "previous":
                targetId = activeOptionId - 1;
                if (targetId < 0) {
                    this.navigate("last");
                    return;
                }
                break;
            case "next":
                targetId = activeOptionId + 1;
                if (targetId > this.state.options.length - 1) {
                    this.navigate("first");
                    return;
                }
                break;
            default:
                return;
        }
        this.state.activeOption = this.state.options.find((o) => o.id === targetId);
    }

    onKeydown(ev) {
        const hotkey = getActiveHotkey(ev);
        switch (hotkey) {
            case "enter":
                if (!this.show || !this.state.activeOption) {
                    return;
                }
                markEventHandled(ev, "NavigableList.select");
                this.selectOption(ev, this.state.activeOption);
                break;
            case "escape":
                if (!this.show) {
                    return;
                }
                markEventHandled(ev, "NavigableList.close");
                this.close();
                break;
            case "tab":
                this.navigate("next");
                if (!this.show) {
                    this.open();
                }
                break;
            case "arrowup":
                this.navigate("previous");
                if (!this.show) {
                    this.open();
                }
                break;
            case "arrowdown":
                this.navigate("next");
                if (!this.show) {
                    this.open();
                }
                break;
            default:
                return;
        }
        ev.preventDefault();
    }

    onOptionMouseEnter(option) {
        this.state.activeOption = option;
    }
}
