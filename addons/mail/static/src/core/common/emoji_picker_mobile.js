import { Component, xml } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { EMOJI_PICKER_PROPS, EmojiPicker } from "@web/core/emoji_picker/emoji_picker";

export class EmojiPickerMobile extends Component {
    static components = { Dialog, EmojiPicker };
    static props = EMOJI_PICKER_PROPS;
    static template = xml`
        <Dialog size="'lg'" header="false" footer="false" contentClass="'o-discuss-mobileContextMenu d-flex position-absolute bottom-0 rounded-0 h-50 bg-100'">
            <EmojiPicker t-props="props"/>
        </Dialog>
    `;
}
