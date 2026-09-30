import { Wysiwyg } from "@html_editor/wysiwyg";
import { Component, markup, onMounted, onWillStart, reactive, useRef, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { localization } from "@web/core/l10n/localization";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { user } from "@web/core/user";
import { useAutofocus, useService } from "@web/core/utils/hooks";
import { isHtmlEmpty } from "@web/core/utils/html";
import { isEmail } from "@web/core/utils/strings";
import { FileUploader } from "@web/views/fields/file_handler";
import { endPos } from "@html_editor/utils/position";

export class ProfileDialog extends Component {
    static template = "website_profile.ProfileDialog";
    static components = {
        Dialog,
        FileUploader,
        Wysiwyg,
    };
    static props = {
        close: Function,
        confirm: { type: Function, optional: true },
        focusWebsiteDescription: {
            type: Boolean,
            optional: true,
        },
        userId: { type: Number },
    };
    static defaultProps = {
        confirm: () => {},
        focusWebsiteDescription: false,
    };

    setup() {
        super.setup();
        this.orm = useService("orm");
        this.upload = useRef("upload");
        this.profileImg = useRef("profileImg");
        this.profileImgData = null;
        this.state = useState({
            isProcessing: false,
            hasError: false,
            emailHasError: false,
            nameHasError: false,
        });
        const websiteDescriptionClass = "website_profile_profile_dialog_website_description";
        useAutofocus({ refName: "name" });

        onWillStart(async () => {
            const [users, countries] = await Promise.all([
                this.orm.read(
                    "res.users",
                    [this.props.userId],
                    [
                        "city",
                        "country_id",
                        "email",
                        "name",
                        "website",
                        "website_description",
                        "website_published",
                    ]
                ),
                this.orm.searchRead("res.country", [], ["id", "name"]),
            ]);
            const userData = users[0];
            userData.country_id = userData.country_id && userData.country_id[0]; // keep only id
            userData.website_description = markup(userData.website_description || "");
            this.user = reactive(userData, () => this.validate());
            this.countries = countries;
            const isInternalUser = await user.hasGroup("base.group_user");
            this.descriptionWysiwygConfig = {
                allowFile: isInternalUser,
                allowImage: isInternalUser,
                classList: ["form-control", websiteDescriptionClass],
                content: this.user.website_description,
                debug: !!this.env.debug,
                direction: localization.direction || "ltr",
                placeholder: _t("Write a few words about yourself..."),
            };
        });

        onMounted(() => {
            if (this.props.focusWebsiteDescription) {
                const websiteDescription = document.querySelector(
                    `.${websiteDescriptionClass}[contenteditable="true"]`
                );
                if (websiteDescription) {
                    document.getSelection()?.setPosition(...endPos(websiteDescription));
                }
            }
            this.validate();
        });
    }

    validate() {
        this.state.emailHasError = !isEmail(this.user.email);
        this.state.nameHasError = !this.user.name || !this.user.name.trim().length;
        this.state.hasError = this.state.emailHasError || this.state.nameHasError;
    }

    get isEditingMyProfile() {
        return user.userId === this.props.userId;
    }

    get title() {
        return _t("Edit Profile");
    }

    onClearProfileImg() {
        this.profileImgData = false;
        this.profileImg.el.src = "/web/static/img/placeholder.png";
    }

    async onConfirm() {
        this.state.isProcessing = true;
        const descriptionElContent = this.websiteDescriptionEditor.getElContent();
        const data = {
            ...this.user,
            country_id: this.user.country_id && parseInt(this.user.country_id),
            website_description: isHtmlEmpty(descriptionElContent.innerText)
                ? ""
                : descriptionElContent.innerHTML,
            user_id: this.props.userId,
        };
        if (this.profileImgData != null) {
            data.image_1920 = this.profileImgData;
        }
        try {
            await rpc("/profile/user/save", data);
            if (this.props.confirm) {
                await this.props.confirm();
            }
            this.props.close();
        } catch (e) {
            const msg = e?.data?.message || e?.message || _t("Update failed.");
            this.env.services.notification.add(msg, { type: "danger" });
        } finally {
            this.state.isProcessing = false;
        }
    }

    onUploadProfileImg(file) {
        this.profileImg.el.src = `data:${file.type};base64,${file.data}`;
        this.profileImgData = file.data;
    }

    onWebsiteDescriptionEditorLoad(editor) {
        this.websiteDescriptionEditor = editor;
    }
}
