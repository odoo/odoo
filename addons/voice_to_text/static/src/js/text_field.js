/** @odoo-module **/

import {TextField} from "@web/views/fields/text/text_field";
import {patch} from "@web/core/utils/patch";
import {useService} from "@web/core/utils/hooks";
import rpc from 'web.rpc';

patch(TextField.prototype, '@web/views/fields/text/text_field', {
    setup() {
        this._super.apply();
        this.notification = useService("notification");
    },
    // This function is used to recognize voice on the text fields
    async recordText(ev) {
        var self = this
        var browser = await rpc.query({
            model: 'voice.recognition',
            method: 'get_the_browser',
            args: [,],
        }).then((data) => {
            console.log(this.notification);
            const closeFun = this.notification.add(
                "Recording....",
                {
                    title: "Recording",
                    type: "success",
                    sticky: true
                },
            );
            setTimeout(() => closeFun(), 15000)
            if (data === 'chrome') {
                let final_transcript = "";
                let interim_transcript = "";  // Define this variable for interim results

                if ("webkitSpeechRecognition" in window) {
                    let speechRecognition = new webkitSpeechRecognition();

                    if (speechRecognition) {
                        speechRecognition.continuous = true;

                        navigator.mediaDevices.getUserMedia({audio: true}).then(() => {
                            speechRecognition.start();
                        });

                        speechRecognition.onresult = (e) => {
                            for (let i = e.resultIndex; i < e.results.length; ++i) {
                                if (e.results[i].isFinal) {
                                    final_transcript += e.results[i][0].transcript;
                                } else {
                                    interim_transcript += e.results[i][0].transcript;
                                }
                            }

                            if (final_transcript) {
                                const field = this.__owl__.bdom.parentEl.attributes.name.nodeValue;
                                const model = this.props.record.resModel;
                                const id = this.env.model.__bm_load_params__.res_id;
                                console.log(id)
                                console.log(final_transcript)
                                rpc.query({
                                    model: 'voice.recognition',
                                    method: 'update_field',
                                    args: [field, model, final_transcript,id],
                                }).then(() => {
                                    this.env.searchModel._notify();
                                });
                            }
                        };
                    }
                }
            }
            else if (data === 'all_browser') {
                const field = this.__owl__.bdom.parentEl.attributes.name.nodeValue;
                const model = this.props.record.resModel;
                const id = this.env.model.__bm_load_params__.res_id;
                rpc.query({
                    model: 'voice.recognition',
                    method: 'update_field',
                    args: [field, model, false, id],
                }).then(() => {
                    this.env.searchModel._notify();
                });
            }
        });


    }
})



