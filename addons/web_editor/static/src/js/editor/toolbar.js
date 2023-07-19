/** @odoo-module **/

import { isMobileOS } from "@web/core/browser/feature_detection";
import { ColorPalette } from "@web_editor/js/wysiwyg/widgets/color_palette";

import {
    Component,
    onMounted,
    useRef,
} from "@odoo/owl";

export class Toolbar extends Component {
    static template = 'web_editor.toolbar';
    static components = { ColorPalette };
    static props = {
        dropDirection: { type: String, optional: true },

        showChecklist: { type: Boolean, optional: true },
        showColors: { type: Boolean, optional: true },
        showFontSize: { type: Boolean, optional: true },
        showHistory: { type: Boolean, optional: true },

        showStyle: { type: Boolean, optional: true },
        showJustify: { type: Boolean, optional: true },
        showList: { type: Boolean, optional: true },
        showLink: { type: Boolean, optional: true },

        showImageShape: { type: Boolean, optional: true },
        showImagePadding: { type: Boolean, optional: true },
        showImageWidth: { type: Boolean, optional: true },
        showImageEdit: { type: Boolean, optional: true },

        showHeading1: { type: Boolean, optional: true },
        showHeading2: { type: Boolean, optional: true },
        showHeading3: { type: Boolean, optional: true },
        showHeading4: { type: Boolean, optional: true },
        showHeading5: { type: Boolean, optional: true },
        showHeading6: { type: Boolean, optional: true },

        onColorpaletteDropdownShow: { type: Function, optional: true },
        onColorpaletteDropdownHide: { type: Function, optional: true },
        textColorPaletteProps: { type: Object },
        backgroundColorPaletteProps: { type: Object },

        slots: { type: Object, optional: true },
    };
    static defaultProps = {
        dropDirection: 'dropdown',

        showChecklist: true,
        showColors: true,
        showFontSize: true,
        showHistory: false,

        showStyle: true,
        showJustify: true,
        showList: true,
        showLink: true,

        showImageShape: true,
        showImagePadding: true,
        showImageWidth: true,
        showImageEdit: true,

        showHeading1: true,
        showHeading2: true,
        showHeading3: true,
        showHeading4: true,
        showHeading5: true,
        showHeading6: true,

        onColorpaletteDropdownShow: () => {},
        onColorpaletteDropdownHide: () => {},
    };

    colorDropdownRef = {
        text: useRef("textColorpickerDropdown"),
        background: useRef("backgroundColorpaletteDropdown"),
    }

    setup() {
        onMounted(() => {
            for (const [colorType, ref] of Object.entries(this.colorDropdownRef)) {
                const dropdown = ref.el;
                if (!dropdown) continue;
                // If the element is within an iframe, access the jquery loaded in
                // the iframe because it is the one who will trigger the dropdown
                // events (i.e hide.bs.dropdown and show.bs.dropdown).
                const $ = dropdown.ownerDocument.defaultView.$;
                const $dropdown = $(dropdown);
                $dropdown.on('show.bs.dropdown', () => {
                    this.props.onColorpaletteDropdownShow(colorType);
                });
                $dropdown.on('hide.bs.dropdown', (ev) => this.props.onColorpaletteDropdownHide(ev));
            }
        });
    }

    isMobile() {
        return isMobileOS();
    }
}
