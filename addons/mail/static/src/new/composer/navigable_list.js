/* @odoo-module **/

import { useService } from "@web/core/utils/hooks";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";
import { usePosition } from "@web/core/position_hook";
import { PartnerImStatus } from "../discuss/partner_im_status"; // Used in composer suggestion template
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
    static components = { PartnerImStatus };
    static template = "mail.navigable_list";
    static props = {
        anchorRef: {},
        position: { type: String, optional: true },
        onSelect: { type: Function },
        sources: {
            type: Array,
            element: {
                type: Object,
                shape: {
                    placeholder: { type: String, optional: true },
                    optionTemplate: { type: String, optional: true },
                    options: [Array, Promise],
                },
            },
        },
        class: { type: String, optional: true },
    };
    static defaultProps = { position: "bottom" };

    setup() {
        this.nextOptionId = 0;
        this.nextSourceId = 0;
        this.rootRef = useRef("root");
        this.sources = [];
        this.state = useState({
            activeSourceOption: null,
            navigationRev: 0,
            open: false,
            optionsRev: 0,
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

    get isOpened() {
        return this.state.open;
    }

    get hasOptions() {
        for (const source of this.sources) {
            if (source.isLoading || source.options.length) {
                return true;
            }
        }
        return false;
    }

    open() {
        this.loadSources();
    }

    close() {
        this.state.open = false;
        this.state.activeSourceOption = null;
    }

    loadSources() {
        this.sources = [];
        const proms = [];
        for (const pSource of this.props.sources) {
            if (pSource.options.length === 0) {
                continue;
            }
            const source = this.makeSource(pSource);
            this.sources.push(source);
            const options = pSource.options;
            if (options instanceof Promise) {
                source.isLoading = true;
                const prom = options.then((options) => {
                    source.options = options.map((option) => this.makeOption(option));
                    source.isLoading = false;
                    if (source.options.length === 0) {
                        this.sources = this.sources.filter((s) => s !== source);
                    }
                    this.state.optionsRev++;
                });
                proms.push(prom);
            } else {
                source.options = options.map((option) => this.makeOption(option));
            }
        }
        Promise.all(proms).then(() => {
            this.navigate(0);
        });
        if (this.sources.length === 0) {
            return;
        }
        this.state.open = true;
    }

    makeOption(option) {
        return Object.assign(Object.create(option), {
            id: ++this.nextOptionId,
        });
    }

    makeSource(source) {
        return {
            id: ++this.nextSourceId,
            options: [],
            isLoading: false,
            placeholder: source.placeholder,
            optionTemplate: source.optionTemplate,
        };
    }

    isActiveSourceOption([sourceIndex, optionIndex]) {
        return (
            this.state.activeSourceOption &&
            this.state.activeSourceOption[0] === sourceIndex &&
            this.state.activeSourceOption[1] === optionIndex
        );
    }

    selectOption(ev, indices, params = {}) {
        const option = this.sources[indices[0]].options[indices[1]];
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
        let step = Math.sign(direction);
        if (!step) {
            this.state.activeSourceOption = null;
            step = 1;
        } else {
            this.state.navigationRev++;
        }
        if (this.state.activeSourceOption) {
            let [sourceIndex, optionIndex] = this.state.activeSourceOption;
            let source = this.sources[sourceIndex];
            optionIndex += step;
            if (0 > optionIndex || optionIndex >= source.options.length) {
                sourceIndex += step;
                source = this.sources[sourceIndex];
                while (source && source.isLoading) {
                    sourceIndex += step;
                    source = this.sources[sourceIndex];
                }
                if (source) {
                    optionIndex = step < 0 ? source.options.length - 1 : 0;
                }
            }
            if (source) {
                this.state.activeSourceOption = [sourceIndex, optionIndex];
            } else {
                this.state.activeSourceOption =
                    direction > 0
                        ? [0, 0]
                        : [
                              this.sources.length - 1,
                              this.sources[this.sources.length - 1].options.length - 1,
                          ];
            }
        } else {
            let sourceIndex = step < 0 ? this.sources.length - 1 : 0;
            let source = this.sources[sourceIndex];
            while (source && source.isLoading) {
                sourceIndex += step;
                source = this.sources[sourceIndex];
            }
            if (source) {
                const optionIndex = step < 0 ? source.options.length - 1 : 0;
                this.state.activeSourceOption = [sourceIndex, optionIndex];
            }
        }
    }

    onKeydown(ev) {
        const hotkey = getActiveHotkey(ev);
        switch (hotkey) {
            case "enter":
                if (!this.isOpened || !this.state.activeSourceOption) {
                    return;
                }
                markEventHandled(ev, "NavigableList.select");
                this.selectOption(ev, this.state.activeSourceOption);
                break;
            case "escape":
                if (!this.isOpened) {
                    return;
                }
                markEventHandled(ev, "NavigableList.close");
                this.close();
                break;
            case "tab":
                this.navigate(+1);
                if (!this.isOpened) {
                    this.open();
                }
                break;
            case "arrowup":
                this.navigate(-1);
                if (!this.isOpened) {
                    this.open();
                }
                break;
            case "arrowdown":
                this.navigate(+1);
                if (!this.isOpened) {
                    this.open();
                }
                break;
            default:
                return;
        }
        ev.preventDefault();
    }

    onOptionMouseEnter(indices) {
        this.state.activeSourceOption = indices;
    }

    onOptionMouseLeave() {
        this.state.activeSourceOption = null;
    }

    onOptionClick(ev, indices) {
        this.selectOption(ev, indices);
    }
}
