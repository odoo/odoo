/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { PDFIframe } from "./PDF_iframe";
import { startSignItemNavigator } from "./sign_item_navigator";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { MobileInputBottomSheet } from "@sign/components/sign_request/mobile_input_bottom_sheet";
import {
    SignNameAndSignatureDialog,
    ThankYouDialog,
    PublicSignerDialog,
    SMSSignerDialog,
    NextDirectSignDialog,
} from "@sign/dialogs/dialogs";

const { DateTime } = luxon;

export class SignablePDFIframe extends PDFIframe {
    /**
     * Renders custom elements inside the PDF.js iframe when signing
     * @param {HTMLIFrameElement} iframe
     * @param {Document} root
     * @param {Object} env
     * @param {Object} owlServices
     * @param {Object} props
     */
    constructor(root, env, owlServices, props) {
        super(root, env, owlServices, props);
        this.currentRole = this.props.currentRole;
        this.currentRoleName = this.props.currentName;
        this.signerName = props.signerName;
        this.frameHash =
            (this.props.frameHash && this.props.frameHash.substring(0, 10) + "...") || "";
    }

    enableCustom(signItem) {
        if (this.readonly || signItem.data.responsible !== this.currentRole) {
            return;
        }
        const signItemElement = signItem.el;
        const signItemData = signItem.data;
        const signItemType = this.signItemTypesById[signItemData.type_id];
        const { name, item_type: type, auto_value: autoValue } = signItemType;
        if (name === _t("Date")) {
            signItemElement.addEventListener("focus", (e) => {
                this.fillTextSignItem(e.currentTarget, DateTime.now().toLocaleString());
            });
        } else if (type === "signature" || type === "initial") {
            signItemElement.addEventListener("click", (e) => {
                this.handleSignatureDialogClick(e.currentTarget, signItemType);
            });
        }

        if (autoValue && ["text", "textarea"].includes(type)) {
            signItemElement.addEventListener("focus", (e) => {
                this.fillTextSignItem(e.currentTarget, autoValue);
            });
        }

        if (this.env.isSmall && ["text", "textarea"].includes(type)) {
            const inputBottomSheet = new MobileInputBottomSheet({
                type: type,
                element: signItemElement,
                value: signItemElement.value,
                label: `${signItemType.tip}: ${signItemType.placeholder}`,
                placeholder: signItemElement.placeholder,
                onTextChange: (value) => {
                    signItemElement.value = value;
                },
                onValidate: (value) => {
                    signItemElement.value = value;
                    signItemElement.dispatchEvent(new Event("input", { bubbles: true }));
                    inputBottomSheet.hide();
                    this.navigator.goToNextSignItem();
                },
                buttonText: _t("next"),
            });

            signItemElement.addEventListener("focus", () => {
                inputBottomSheet.updateInputText(signItemElement.value);
                inputBottomSheet.show();
            });
        }

        if (type === "selection") {
            if (signItemElement.value) {
                this.handleInput();
            }
            const optionDiv = signItemElement.querySelector(".o_sign_select_options_display");
            optionDiv.addEventListener("click", (e) => {
                if (e.target.classList.contains("o_sign_item_option")) {
                    const option = e.target;
                    const selectedValue = option.dataset.id;
                    signItemElement.value = selectedValue;
                    option.classList.add("o_sign_selected_option");
                    option.classList.remove("o_sign_not_selected_option");
                    const notSelected = optionDiv.querySelectorAll(
                        `.o_sign_item_option:not([data-id='${selectedValue}'])`
                    );
                    [...notSelected].forEach((el) => {
                        el.classList.remove("o_sign_selected_option");
                        el.classList.add("o_sign_not_selected_option");
                    });
                    this.handleInput();
                }
            });
        }

        signItemElement.addEventListener("input", this.handleInput.bind(this));
    }

    handleInput() {
        this.checkSignItemsCompletion();
        this.navigator.setTip(_t("next"));
    }

    /**
     * Logic for wizard/mark behavior is:
     * If auto_value is defined and the item is not marked yet, auto_value is used
     * Else, wizard is opened.
     * @param { HTMLElement } signatureItem
     * @param { Object } type
     */
    handleSignatureDialogClick(signatureItem, signItemType) {
        this.refreshSignItems();
        const signature = signatureItem.dataset.signature;
        const { auto_value: autoValue, frame_value: frameValue, item_type: type } = signItemType;
        if (autoValue && !signature) {
            Promise.all([
                this.adjustSignatureSize(autoValue, signatureItem),
                this.adjustSignatureSize(frameValue, signatureItem),
            ]).then(([data, frameData]) => {
                this.fillItemWithSignature(signatureItem, data, { frame: frameData, hash: "0" });
                this.handleInput();
            });
        } else if (type === "initial" && this.nextInitial && !signature) {
            this.adjustSignatureSize(this.nextInitial, signatureItem).then((data) => {
                this.fillItemWithSignature(signatureItem, data);
                this.handleInput();
            });
        } else {
            this.openSignatureDialog(signatureItem, signItemType);
        }
    }

    fillTextSignItem(signItemElement, value) {
        if (signItemElement.value === "") {
            signItemElement.value = value;
            this.handleInput();
        }
    }

    /**
     * Adjusts signature/initial size to fill the dimensions of the sign item box
     * @param { String } data base64 image
     * @param { HTMLElement } signatureItem
     * @returns { Promise }
     */
    adjustSignatureSize(data, signatureItem) {
        if (!data) {
            return Promise.resolve(false);
        }
        return new Promise((resolve, reject) => {
            const img = new Image();
            img.onload = () => {
                const c = document.createElement("canvas");
                if (
                    !signatureItem.parentElement ||
                    !signatureItem.parentElement.classList.contains("page")
                ) {
                    // checks if element is detached from pdf js
                    this.refreshSignItems();
                }
                const { width: boxWidth, height: boxHeight } =
                    signatureItem.getBoundingClientRect();
                const imgHeight = img.height;
                const imgWidth = img.width;
                const ratioBoxWidthHeight = boxWidth / boxHeight;
                const ratioImageWidthHeight = imgWidth / imgHeight;

                const [canvasHeight, canvasWidth] =
                    ratioBoxWidthHeight > ratioImageWidthHeight
                        ? [imgHeight, imgHeight * ratioBoxWidthHeight]
                        : [imgWidth / ratioBoxWidthHeight, imgWidth];

                c.height = canvasHeight;
                c.width = canvasWidth;

                const ctx = c.getContext("2d");
                const oldShadowColor = ctx.shadowColor;
                ctx.shadowColor = "transparent";
                ctx.drawImage(
                    img,
                    c.width / 2 - img.width / 2,
                    c.height / 2 - img.height / 2,
                    img.width,
                    img.height
                );
                ctx.shadowColor = oldShadowColor;
                resolve(c.toDataURL());
            };
            img.src = data;
        });
    }

    fillItemWithSignature(signatureItem, image, frameData = false) {
        signatureItem.dataset.signature = image;
        signatureItem.replaceChildren();
        const signHelperSpan = document.createElement("span");
        signHelperSpan.classList.add("o_sign_helper");
        signatureItem.append(signHelperSpan);
        if (frameData && frameData.frame) {
            signatureItem.dataset.frameHash = frameData.hash;
            signatureItem.dataset.frame = frameData.frame;
            const frameImage = document.createElement("img");
            frameImage.src = frameData.frame;
            frameImage.classList.add("o_sign_frame");
            signatureItem.append(frameImage);
        } else {
            delete signatureItem.dataset.frame;
        }
        const signatureImage = document.createElement("img");
        signatureImage.src = image;
        signatureItem.append(signatureImage);
    }

    closeDialog() {
        this.closeFn && this.closeFn();
        this.closeFn = false;
    }

    /**
     * Opens the signature dialog
     * @param { HTMLElement } signatureItem
     * @param {*} type
     */
    openSignatureDialog(signatureItem, type) {
        if (this.dialogOpen) {
            return;
        }
        const signature = {
            name: this.signerName || "",
        };
        const frame = {};
        const { height, width } = signatureItem.getBoundingClientRect();
        const signFrame = signatureItem.querySelector(".o_sign_frame");
        this.dialogOpen = true;
        this.closeFn = this.dialog.add(
            SignNameAndSignatureDialog,
            {
                frame,
                signature,
                signatureType: type.item_type,
                displaySignatureRatio: width / height,
                activeFrame: Boolean(signFrame) || !type.auto_value,
                mode: type.auto_value ? "draw" : "auto",
                defaultFrame: type.frame_value || "",
                hash: this.frameHash,
                onConfirm: async () => {
                    if (!signature.isSignatureEmpty && signature.signatureChanged) {
                        const signatureName = signature.name;
                        this.signerName = signatureName;
                        await frame.updateFrame();
                        const frameData = frame.getFrameImageSrc();
                        const signatureSrc = `data:${signature.getSignatureImage().join(", ")}`;
                        type.auto_value = signatureSrc;
                        type.frame_value = frameData;
                        if (this.user.userId) {
                            await this.updateUserSignature(type);
                        }
                        this.fillItemWithSignature(signatureItem, signatureSrc, {
                            frame: frameData,
                            hash: this.frameHash,
                        });
                    } else if (signature.signatureChanged) {
                        // resets the sign item
                        delete signatureItem.dataset.signature;
                        delete signatureItem.dataset.frame;
                        signatureItem.replaceChildren();
                        const signHelperSpan = document.createElement("span");
                        signHelperSpan.classList.add("o_sign_helper");
                        signatureItem.append(signHelperSpan);
                        if (type.placeholder) {
                            const placeholderSpan = document.createElement("span");
                            placeholderSpan.classList.add("o_placeholder");
                            placeholderSpan.innerText = type.placeholder;
                            signatureItem.append(placeholderSpan);
                        }
                    }
                    this.closeDialog();
                    this.handleInput();
                },
                onConfirmAll: async () => {
                    const signatureName = signature.name;
                    this.signerName = signatureName;
                    await frame.updateFrame();
                    const frameData = frame.getFrameImageSrc();
                    const signatureSrc = `data:${signature.getSignatureImage().join(", ")}`;
                    type.auto_value = signatureSrc;
                    type.frame_value = frameData;
                    if (this.user.userId) {
                        await this.updateUserSignature(type);
                    }
                    for (const page in this.signItems) {
                        await Promise.all(
                            Object.values(this.signItems[page]).reduce((promiseList, signItem) => {
                                if (
                                    signItem.data.responsible === this.currentRole &&
                                    signItem.data.type_id === type.id
                                ) {
                                    promiseList.push(
                                        Promise.all([
                                            this.adjustSignatureSize(signatureSrc, signItem.el),
                                            this.adjustSignatureSize(frameData, signItem.el),
                                        ]).then(([data, frameData]) => {
                                            this.fillItemWithSignature(signItem.el, data, {
                                                frame: frameData,
                                                hash: this.frameHash,
                                            });
                                        })
                                    );
                                }
                                return promiseList;
                            }, [])
                        );
                    }
                    this.closeDialog();
                    this.handleInput();
                },
                onCancel: () => {
                    this.closeDialog();
                },
            },
            {
                onClose: () => {
                    this.dialogOpen = false;
                },
            }
        );
    }

    checkSignItemsCompletion() {
        this.refreshSignItems();
        const itemsToSign = [];
        for (const page in this.signItems) {
            Object.values(this.signItems[page]).forEach((signItem) => {
                if (
                    signItem.data.required &&
                    signItem.data.responsible === this.currentRole &&
                    !signItem.data.value
                ) {
                    const el =
                        signItem.data.isEditMode && signItem.el.type === "text"
                            ? el.querySelector("input")
                            : signItem.el;
                    const uncheckedBox = el.value === "on" && !el.checked;
                    if (!((el.value && el.value.trim()) || el.dataset.signature) || uncheckedBox) {
                        itemsToSign.push(signItem);
                    }
                }
            });
        }

        itemsToSign.length ? this.hideBanner() : this.showBanner();
        this.navigator.toggle(itemsToSign.length > 0);
        return itemsToSign;
    }

    showBanner() {
        this.props.validateBanner.style.display = "block";
        const an = this.props.validateBanner.animate(
            { opacity: 1 },
            { duration: 500, fill: "forwards" }
        );
        an.finished.then(() => {
            if (this.env.isSmall) {
                this.props.validateBanner.scrollIntoView({
                    behavior: "smooth",
                    block: "center",
                    inline: "center",
                });
            }
        });
    }

    hideBanner() {
        this.props.validateBanner.style.display = "none";
        this.props.validateBanner.style.opacity = 0;
    }

    /**
     * Updates the user's signature in the res.user model
     * @param { Object } type
     */
    updateUserSignature(type) {
        return this.rpc("/sign/update_user_signature", {
            sign_request_id: this.props.requestID,
            role: this.currentRole,
            signature_type: type.item_type === "signature" ? "sign_signature" : "sign_initials",
            datas: type.auto_value,
            frame_datas: type.frame_value,
        });
    }

    /**
     * Extends the rendering context of the sign item based on its data
     * @param {SignItem.data} signItem
     * @returns {Object}
     */
    getContext(signItem) {
        return super.getContext(signItem);
    }

    /**
     * Hook executed before rendering the sign items and the sidebar
     */
    preRender() {
        super.preRender();
    }

    postRender() {
        super.postRender();
        if (this.readonly) {
            return;
        }
        this.navigator = startSignItemNavigator(
            this,
            this.root.querySelector("#viewerContainer"),
            this.signItemTypesById,
            this.env
        );
        this.checkSignItemsCompletion();

        this.root.querySelector("#viewerContainer").addEventListener("scroll", () => {
            if (!this.navigator.state.isScrolling && this.navigator.state.started) {
                this.navigator.setTip(_t("next"));
            }
        });

        this.root.querySelector("#viewerContainer").addEventListener("keydown", (e) => {
            if (e.key !== "Enter" || (e.target.tagName.toLowerCase() === 'textarea')) {
                return;
            }
            this.navigator.goToNextSignItem();
        });

        this.props.validateBanner
            .querySelector(".o_validate_button")
            .addEventListener("click", () => {
                this.signDocument();
            });
    }

    getMailFromSignItems() {
        let mail = "";
        for (const page in this.signItems) {
            Object.values(this.signItems[page]).forEach(({ el }) => {
                const childInput = el.querySelector("input");
                const value = el.value || (childInput && childInput.value);
                if (value && value.indexOf("@") >= 0) {
                    mail = value;
                }
            });
        }
        return mail;
    }

    signDocument() {
        this.props.validateBanner.setAttribute("disabled", true);
        this.signatureInfo = { name: this.signerName || "", mail: this.getMailFromSignItems() };

        [
            this.signatureInfo.signatureValues,
            this.signatureInfo.frameValues,
            this.signatureInfo.newSignItems,
        ] = this.getSignatureValuesFromConfiguration();
        if (!this.signatureInfo.signatureValues) {
            this.checkSignItemsCompletion();
            this.dialog.add(AlertDialog, {
                title: _t("Warning"),
                body: _t("Some fields have still to be completed"),
            });
            this.props.validateButton.textContent = this.props.validateButtonText;
            this.props.validateBanner.removeAttribute("disabled");
            return;
        }
        this.signatureInfo.hasNoSignature =
            Object.keys(this.signatureInfo.signatureValues).length == 0 &&
            Object.keys(this.signItems).length == 0;
        this._signDocument();
    }

    async _signDocument() {
        this.props.validateButton.textContent = this.props.validateButtonText;
        this.props.validateButton.setAttribute("disabled", true);
        if (this.signatureInfo.hasNoSignature) {
            const signature = {
                name: this.signerName || "",
            };
            this.closeFn = this.dialog.add(SignNameAndSignatureDialog, {
                signature,
                onConfirm: () => {
                    this.signatureInfo.name = signature.name;
                    this.signatureInfo.signatureValues = signature.getSignatureImage()[1];
                    this.signatureInfo.frameValues = [];
                    this.signatureInfo.hasNoSignature = false;
                    this.closeDialog();
                    this._signDocument();
                },
                onCancel: () => {
                    this.closeDialog();
                },
            });
        } else if (this.props.isUnknownPublicUser) {
            this.closeFn = this.dialog.add(
                PublicSignerDialog,
                {
                    name: this.signatureInfo.name,
                    mail: this.signatureInfo.mail,
                    postValidation: async (requestID, requestToken, accessToken) => {
                        this.signInfo.set({
                            documentId: requestID,
                            signRequestToken: requestToken,
                            signRequestItemToken: accessToken,
                        });
                        this.props.requestID = requestID;
                        this.props.requestToken = requestToken;
                        this.props.accessToken = accessToken;
                        if (this.props.coords) {
                            await this.rpc(
                                `/sign/save_location/${requestID}/${accessToken}`,
                                this.props.coords
                            );
                        }
                        this.props.isUnknownPublicUser = false;
                        this._signDocument();
                    },
                },
                {
                    onClose: () => {
                        this.props.validateButton.removeAttribute("disabled");
                    },
                }
            );
        } else if (this.props.authMethod) {
            this.openAuthDialog();
        } else {
            this._sign();
        }
    }

    _getRouteAndParams() {
        const route = this.signatureInfo.smsToken
            ? `/sign/sign/${encodeURIComponent(this.props.requestID)}/${encodeURIComponent(
                  this.props.accessToken
              )}/${encodeURIComponent(this.signatureInfo.smsToken)}`
            : `/sign/sign/${encodeURIComponent(this.props.requestID)}/${encodeURIComponent(
                  this.props.accessToken
              )}`;

        const params = {
            signature: this.signatureInfo.signatureValues,
            frame: this.signatureInfo.frameValues,
            new_sign_items: this.signatureInfo.newSignItems,
        };

        return [route, params];
    }

    async _sign() {
        const [route, params] = this._getRouteAndParams();
        this.ui.block();
        const response = await this.rpc(route, params).finally(() => this.ui.unblock());
        this.props.validateButton.textContent = this.props.validateButtonText;
        this.props.validateButton.removeAttribute("disabled");
        if (response.success) {
            if (response.url) {
                document.location.pathname = response.url;
            } else {
                this.disableItems();
                // only available in backend
                const nameList = this.signInfo.get("nameList");
                if (nameList && nameList.length > 0) {
                    this.dialog.add(NextDirectSignDialog);
                } else {
                    this.openThankYouDialog();
                }
            }
            this.hideBanner();
        } else {
            if (response.sms) {
                this.dialog.add(AlertDialog, {
                    title: _t("Error"),
                    body: _t(
                        "Your signature was not submitted. Ensure the SMS validation code is correct."
                    ),
                });
            } else {
                this.dialog.add(
                    AlertDialog,
                    {
                        title: _t("Error"),
                        body: _t(
                            "Sorry, an error occurred, please try to fill the document again."
                        ),
                    },
                    {
                        onClose: () => {
                            window.location.reload();
                        },
                    }
                );
            }
            this.props.validateButton.setAttribute("disabled", true);
        }
    }

    /**
     * Gets the signature values from the sign items
     * Gets the frame values
     * Gets the sign items that were added in edit while signing
     * @returns { Array } [signature values, frame values, added sign items]
     */
    getSignatureValuesFromConfiguration() {
        const signatureValues = {};
        const frameValues = {};
        const newSignItems = {};
        for (const page in this.signItems) {
            for (const item of Object.values(this.signItems[page])) {
                const responsible = item.data.responsible || 0;
                if (responsible > 0 && responsible !== this.currentRole) {
                    continue;
                }

                const value = this.getSignatureValueFromElement(item);
                const [frameValue, frameHash] = item.el.dataset.signature
                    ? [item.el.dataset.frame, item.el.dataset.frameHash]
                    : [false, false];

                if (!value) {
                    if (item.data.required) {
                        return [{}, {}];
                    }
                    continue;
                }

                signatureValues[item.data.id] = value;
                frameValues[item.data.id] = { frameValue, frameHash };
                if (item.data.isSignItemEditable) {
                    newSignItems[item.data.id] = {
                        type_id: item.data.type_id,
                        required: item.data.required,
                        name: item.data.name || false,
                        option_ids: item.data.option_ids,
                        responsible_id: responsible,
                        page: page,
                        posX: item.data.posX,
                        posY: item.data.posY,
                        width: item.data.width,
                        height: item.data.height,
                    };
                }
            }
        }

        return [signatureValues, frameValues, newSignItems];
    }

    getSignatureValueFromElement(item) {
        const types = {
            text: () => {
                const textValue =
                    item.el.textContent && item.el.textContent.trim() ? item.el.textContent : false;
                const value =
                    item.el.value && item.el.value.trim()
                        ? item.el.value
                        : item.el.querySelector("input")?.value || false;
                return value || textValue;
            },
            initial: () => item.el.dataset.signature,
            signature: () => item.el.dataset.signature,
            textarea: () => this.textareaApplyLineBreak(item.el),
            selection: () => (item.el.value && item.el.value.trim() ? item.el.value : false),
            checkbox: () => {
                if (item.el.checked) {
                    return "on";
                } else {
                    return item.data.required ? false : "off";
                }
            },
        };
        const type = item.data.type;
        return type in types ? types[type]() : types["text"]();
    }

    textareaApplyLineBreak(element) {
        // Removing wrap in order to have scrollWidth > width
        element.setAttribute("wrap", "off");

        const strRawValue = element.value;
        element.value = "";

        const nEmptyWidth = element.scrollWidth;
        let nLastWrappingIndex = -1;

        // Computing new lines
        strRawValue.split("").forEach((curChar, i) => {
            element.value += curChar;

            if (curChar === " " || curChar === "-" || curChar === "+") {
                nLastWrappingIndex = i;
            }

            if (element.scrollWidth > nEmptyWidth) {
                let buffer = "";
                if (nLastWrappingIndex >= 0) {
                    for (let j = nLastWrappingIndex + 1; j < i; j++) {
                        buffer += strRawValue.charAt(j);
                    }
                    nLastWrappingIndex = -1;
                }
                buffer += curChar;
                element.value = element.value.substr(0, element.value.length - buffer.length);
                element.value += "\n" + buffer;
            }
        });
        element.setAttribute("wrap", "");
        return element.value;
    }

    disableItems() {
        const items = this.root.querySelectorAll(".o_sign_sign_item");
        for (const item of Array.from(items)) {
            item.classList.add("o_sign_sign_item_pdfview");
        }
    }

    openThankYouDialog() {
        this.dialog.add(ThankYouDialog, {
            redirectURL: this.props.redirectURL,
            redirectURLText: this.props.redirectURLText,
        });
    }

    async openAuthDialog() {
        const authDialog = await this.getAuthDialog();
        if (authDialog.component) {
            this.closeFn = this.dialog.add(authDialog.component, authDialog.props, {
                onClose: () => {
                    this.props.validateButton.removeAttribute("disabled");
                },
            });
        } else {
            this._sign();
        }
    }

    async getAuthDialog() {
        if (this.props.authMethod === "sms" && !this.signatureInfo.smsToken) {
            const credits = await this.rpc("/sign/has_sms_credits");
            if (credits) {
                return {
                    component: SMSSignerDialog,
                    props: {
                        signerPhone: this.props.signerPhone,
                        postValidation: (code) => {
                            this.signatureInfo.smsToken = code;
                            return this._signDocument();
                        },
                    },
                };
            }
            return false;
        }
        return false;
    }
}
