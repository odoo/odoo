/** @odoo-module **/

import { Component, onMounted, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { redirect } from "@web/core/utils/urls";
import { SelectMenu } from "@web/core/select_menu/select_menu";
import { ModuleToInstallIcon, SlideCategoryIcon } from "./slide_upload_dialog_select";
import { SlideInstallModule } from "./slide_install_module";
import { SlideUploadCategory } from "./slide_upload_category";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";

export class SlideUploadDialog extends Component {
    static baseSettings = {
        modulesToInstallMsg: "",
        page: "select",
        size: "md",
        alertMsg: "",
        title: _t("Add Content"),
        installModuleData: null,
    };
    static categoryData = {
        document: { icon: "fa-file-pdf-o", label: _t("Document") },
        infographic: { icon: "fa-file-image-o", label: _t("Image") },
        article: { icon: "fa-file-text", label: _t("Article") },
        video: { icon: "fa-file-video-o", label: _t("Video") },
        quiz: { icon: "fa-question-circle", label: _t("Quiz") },
    };
    static components = {
        Dialog,
        DropdownItem,
        ModuleToInstallIcon,
        SelectMenu,
        SlideCategoryIcon,
        SlideUploadCategory,
        SlideInstallModule,
    };
    static pagesTemplates = {
        article: "website_slides.SlideCategoryTutorial.Article",
        document: "website_slides.SlideCategoryTutorial.Document",
        infographic: "website_slides.SlideCategoryTutorial.Infographic",
        select: "website_slides.SlideUploadDialogSelect",
        install_module: "website_slides.UploadDialogInstallModule",
        upload: "website_slides.UploadInProgressDialog",
        video: "website_slides.SlideCategoryTutorial.Video",
        quiz: "website_slides.SlideCategoryTutorial.Quiz",
    };
    static props = {
        canPublish: Boolean,
        canUpload: Boolean,
        categoryId: { type: String, optional: true },
        channelId: Number,
        close: Function,
        modulesToInstall: { type: Array, optional: true },
        openModal: { type: String, optional: true },
    };
    static template = "website_slides.SlideUploadDialog";

    setup() {
        this.defaultCategoryID = parseInt(this.props.categoryId, 10);
        this.modulesToInstallStatus = null;
        this.dialog = useService("dialog");
        this.orm = useService("orm");
        this.pagesTemplates = this.constructor.pagesTemplates;
        this.slideCategoryData = this.constructor.categoryData;
        this.state = useState({ ...this.constructor.baseSettings });
        onMounted(() => {
            if (this.props.openModal && this.props.openModal in this.slideCategoryData) {
                // Sets the appropriate category's upload template if one has to be opened on load.
                this.onClickSlideCategoryIcon(this.props.openModal);
            }
        });
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    onClickSlideCategoryIcon(slideCategory) {
        this.state.page = slideCategory;
        this.state.size = "lg";
    }

    onClickInstallModuleIcon(moduleId) {
        this.state.page = "install_module";
        this.state.installModuleData = this.props.modulesToInstall.find((m) => m.id === moduleId);
        this.state.size = "md";
    }

    onClickGoBack() {
        Object.assign(this.state, SlideUploadDialog.baseSettings);
    }

    /**
     * Show the upload page while processing new slide submission
     */
    async uploadSlide(formValues, previousPage) {
        this.state.page = "upload";
        this.state.size = "md";
        const data = await rpc("/slides/add_slide", formValues);
        if (data.error) {
            this.state.page = previousPage;
            this.state.size = "lg";
            this.state.alertMsg = data.error;
            return;
        }
        if (data.url.includes("enable_editor")) {
            // If we need to enter edit mode, it should be done to the top
            // window so that we end up refreshing the backend client action
            // in edit mode.
            const { origin, pathname } = window.top.location;
            const url = new URL(data.url, `${origin}${pathname}`);
            if (url.origin === origin) {
                window.top.location = url.href;
            }
        } else {
            redirect(data.url);
        }
    }
}
