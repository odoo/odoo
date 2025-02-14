import { Component, markRaw, reactive, useChildSubEnv, xml } from "@odoo/owl";
import { registry } from "@web/core/registry";

class BottomSheetWrapper extends Component {
    static template = xml`<t t-component="props.subComponent" t-props="props.subProps" />`;
    static props = ["*"];
    setup() {
        useChildSubEnv({ bottomSheetData: this.props.subEnv });
    }
}

export const bottomSheetService = {
    dependencies: ["overlay"],
    start(env, { overlay }) {
        const sheets = reactive({});
        let nextId = 0;

        const deactivate = () => {
            for (const id in sheets) {
                sheets[id].isActive = false;
            }
        };

        const add = (bottomSheetClass, props, options = {}) => {
            const id = nextId++;
            const closeFn = () => close(id);
            
            deactivate();
            
            const subEnv = reactive({
                id,
                close: closeFn,
                dismiss: closeFn,
                isActive: true,
            });

            const remove = overlay.add(
                BottomSheetWrapper,
                {
                    subComponent: bottomSheetClass,
                    subProps: markRaw({ ...props, close: closeFn }),
                    subEnv,
                },
                {
                    onRemove: () => {
                        if (sheets[id]) {
                            delete sheets[id];
                            if (Object.keys(sheets).length === 0) {
                                document.body.classList.remove("bottom-sheet-open");
                            }
                            options.onClose?.();
                        }
                    },
                }
            );

            sheets[id] = {
                id,
                remove,
                onClose: options.onClose,
            };
            
            document.body.classList.add("bottom-sheet-open");
            return closeFn;
        };

        function close(id) {
            if (sheets[id]) {
                const sheet = sheets[id];
                sheet.remove();
            }
        }

        function closeAll() {
            for (const id in sheets) {
                close(id);
            }
        }

        return { add, closeAll };
    },
};

registry.category("services").add("bottomSheet", bottomSheetService);

