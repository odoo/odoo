/** @odoo-module **/

import {SearchBar} from "@web/search/search_bar/search_bar";
import {patch} from "@web/core/utils/patch";
import rpc from 'web.rpc';
import {useService} from "@web/core/utils/hooks";

const {useEffect, useState} = owl;

patch(SearchBar.prototype, '@web/search/search_bar/search_bar', {
    setup() {
        this._super(...arguments);
        this.microphone = false;
        this.data = useState({
            response: false
        });
        this.notification = useService("notification");
        useEffect(() => {
            this.onSearchInput();
        }, () => [this.data.response]);
    },

    // Function to recognize the voice in the search bar
    async recordVoiceBar() {
        this.microphone = true;

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
            try {
                const response = await rpc.query({
                    model: 'voice.recognition',
                    method: 'recognize_speech',
                    args: [],
                });
                this.data.response = response || false;
                if (!response) {
                    this.notification.add(
                        "Couldn't recognize the voice, please try again.",
                        {
                            title: "Recording",
                            type: "info",
                        },
                    )
                }
            } catch (error) {
                console.error("RPC error: ", error);
            }
        }
    },

    onSearchInput(ev) {
        let query = ev?.target?.value?.trim();

        if (this.microphone && this.data.response) {
            query = this.data.response;
            this.microphone = false;
        }

        if (query) {
            this.computeState({query, expanded: [], focusedIndex: 0, subItems: []});
        } else if (this.items.length) {
            this.resetState();
        }
    }
});
