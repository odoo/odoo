import { Component, onMounted, useRef, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

export class TextInputWithTagPopup extends Component {
    static template = "point_of_sale.TextInputWithTagPopup";
    static components = { Dialog };
    static props = {
        title: String,
        buttons: { type: Array, optional: true },
        startingValue: { type: String, optional: true },
        placeholder: { type: String, optional: true },
        rows: { type: Number, optional: true },
        getPayload: Function,
        close: Function,
    };
    static defaultProps = {
        startingValue: "",
        placeholder: "",
        rows: 1,
        buttons: [],
    };

    setup() {
        this.state = useState({
            inputValue: this.props.startingValue,
            tagList: [],
        });
        this.inputRef = useRef("input");
        onMounted(this.onMounted);
        this.fillTagList(this.props.startingValue);
    }
    onMounted() {
        this.inputRef.el.focus();
        this.inputRef.el.select();
    }

    onClickTextContainer() {
        this.inputRef.el.focus();
    }

    confirm() {
        if (this.inputRef.el.value !== "") {
            this.state.tagList.push(this.inputRef.el.value);
        }

        let contentToSave = "";
        for (const index in this.state.tagList) {
            contentToSave += this.state.tagList[index] + "\n";
        }
        this.props.getPayload(contentToSave);
        this.props.close();
    }

    fillTagList(textBrut) {
        if (textBrut.length > 0) {
            const lines = textBrut.split("\n").filter((line) => line !== "");
            for (const index in lines) {
                this.state.tagList.push(lines[index]);
            }
        }
    }

    close() {
        this.state.tagList = [];
        this.fillTagList(this.state.inputValue);
        let contentToSave = "";
        for (const index in this.state.tagList) {
            contentToSave += this.state.tagList[index] + "\n";
        }
        this.props.getPayload(contentToSave);
        this.props.close();
    }

    buttonClick(button) {
        if (this.state.tagList.includes(button.label)) {
            const index = this.state.tagList.indexOf(button.label);
            if (index > -1) {
                this.state.tagList.splice(index, 1);
            }
            button.isSelected = false;
        } else {
            this.state.tagList.push(button.label);
            button.isSelected = true;
        }
    }

    onKeydown(ev) {
        console.log(this.inputRef.el.value);
        if (ev.key.toUpperCase() === "ENTER") {
            this.state.tagList.push(this.inputRef.el.value);
            this.inputRef.el.value = "";
        }

        if (
            ev.key.toUpperCase() === "BACKSPACE" &&
            this.inputRef.el.value === "" &&
            this.state.tagList.length > 0
        ) {
            this.state.tagList.pop();
        }
    }
}
