/* @odoo-module */

import { registry } from "@web/core/registry";
const { Component, onWillStart, onMounted, useRef, useState } = owl;
import { loadJS, loadCSS } from "@web/core/assets"

export class OwlValid extends Component {
    setup(){
    this.phone = useRef("phone")
    this.file = useRef("file")
    this.iti
    this.state = useState({ phoneValid: undefined })

        onWillStart(async ()=>{
            await loadJS("/validator/static/src/lib/inti-tel-input/build/js/intlTelInput.min.js")
            await loadCSS("/validator/static/src/lib/inti-tel-input/build/css/intlTelInput.css")

            await loadJS("https://unpkg.com/filepond@^4/dist/filepond.js")
            await loadCSS("https://unpkg.com/filepond@^4/dist/filepond.css")

            await loadJS("https://unpkg.com/filepond-plugin-image-preview/dist/filepond-plugin-image-preview.js")
            await loadCSS("https://unpkg.com/filepond-plugin-image-preview/dist/filepond-plugin-image-preview.css")
        })

        onMounted(()=>{
            console.log("intlTelInput", intlTelInput)
            this.iti = intlTelInput(this.phone.el, {initialCountry: "in",
                utilsScript: "https://cdn.jsdelivr.net/npm/intl-tel-input@23.0.11/build/js/utils.js",
              })

              console.log("FilePond", FilePond)


              FilePond.registerPlugin(FilePondPluginImagePreview);

              FilePond.create(this.file.el, {
                allowMultiple: true,
                server: {
                        process: './filepond/process',
                        fetch: null,
                        revert: './filepond/revert',
                    },
              })
        })
    }

    validate(){
        //console.log("this.iti", this.iti)
        const number = this.iti.getNumber()
        const country = this.iti.getSelectedCountryData()

        console.log("number, country ===>", number, country)

        if(this.iti.isValidNumber()){
            console.log("Phone is valid")
            this.state.phoneValid = true
        } else {
            console.log("Phone is not valid")
            this.state.phoneValid = false
        }

    }
}

OwlValid.template = 'owl.validator';

registry.category("actions").add("owl.validator", OwlValid);