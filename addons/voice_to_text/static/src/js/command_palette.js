/** @odoo-module **/
import {CommandPalette} from "@web/core/commands/command_palette";
import {patch} from "@web/core/utils/patch";
import {useService} from "@web/core/utils/hooks";
import rpc from 'web.rpc';

patch(CommandPalette.prototype, '@web/core/commands/command_palette', {
    setup() {
        this._super.apply();
        this.notification = useService("notification");
    },
    //This function is used to recognize the voice
    async recordVoice(event) {
        if (location.href.includes('http:')) {
            const closeFun = this.notification.add(
                "Recording....",
                {
                    title: "Recording",
                    type: "success",
                    sticky: true
                },
            );
            setTimeout(() => closeFun(), 15000)
            var response = await rpc.query({
                model: 'voice.recognition',
                method: 'recognize_speech',
                args: [],
            })
            if (response) {
                this.state.searchValue = response
            } else {
                this.notification.add(
                    "Couldn't recognize the voice, please try again.",
                    {
                        title: "Recording",
                        type: "info",
                    },
                )
            }
        }
    },
})