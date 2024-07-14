/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { downloadFile } from "@web/core/network/download";
import { getDataURLFromFile, getOrigin } from "@web/core/utils/urls";
import { FileModel } from "@web/core/file_viewer/file_model";
import { useFileViewer } from "@web/core/file_viewer/file_viewer_hook";
import { useService } from "@web/core/utils/hooks";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { renderToElement } from "@web/core/utils/render";

import {
    onMounted,
    useEffect,
    useRef,
    useState,
} from "@odoo/owl";

import { setSelection, rightPos } from "@web_editor/js/editor/odoo-editor/src/utils/utils";

import { AttachToMessageMacro, UseAsAttachmentMacro } from "@knowledge/macros/file_macros";
import { AbstractBehavior } from "@knowledge/components/behaviors/abstract_behavior/abstract_behavior";
import {
    BehaviorToolbar,
    BehaviorToolbarButton,
} from "@knowledge/components/behaviors/behavior_toolbar/behavior_toolbar";
import {
    copyOids,
    decodeDataBehaviorProps,
    encodeDataBehaviorProps,
    getPropNameNode,
    useRefWithSingleCollaborativeChild,
} from "@knowledge/js/knowledge_utils";

export class FileBehavior extends AbstractBehavior {
    static components = {
        BehaviorToolbar,
        BehaviorToolbarButton,
    };
    static props = {
        ...AbstractBehavior.props,
        // TODO ABD make it not optional after upgrade
        fileData: { type: Object, optional: true },

        // TODO ABD remove obsolete props after upgrade
        fileExtension: { type: String, optional: true },
        fileImage: { type: Object, optional: true },
        fileName: { type: String, optional: true },
    };
    static template = "knowledge.FileBehavior";

    setup() {
        super.setup();
        this.actionService = useService('action');
        this.dialogService = useService('dialog');
        this.rpcService = useService('rpc');
        this.uiService = useService('ui');
        this.macrosServices = {
            action: this.actionService,
            dialog: this.dialogService,
            ui: this.uiService,
        };
        this.targetRecordInfo = this.knowledgeCommandsService.getCommandsRecordInfo();

        // TODO ABD change `this.fileData` to `this.props.fileData` when
        // upgrade is properly implemented.
        this.state = useState({
            fileModel: Object.assign(new FileModel(), this.fileData),
            editFileName: false,
        });
        this.attachmentViewer = useFileViewer();
        this.fileNameRef = useRefWithSingleCollaborativeChild(
            'fileNameRef',
            (element) => {
                const fileName = this.fileNameSpanTextContent;
                if (element && fileName.length) {
                    this.setFileName(fileName);
                } else {
                    this.renderFileName();
                    this.editor.historyStep();
                }
            }
        );
        if (!this.props.readonly) {
            this.nameInput = useRef('nameInput');
            useEffect(() => {
                if (this.state.editFileName) {
                    this.nameInput.el.value = this.state.fileModel.filename;
                    this.nameInput.el.focus();
                    this.nameInput.el.select();
                }
            }, () => [this.state.editFileName]);
            useEffect(() => {
                if (this.state.fileModel.filename !== this.fileNameSpanTextContent) {
                    this.renderFileName();
                    this.editor.historyStep();
                }
            }, () => [this.state.fileModel.filename]);
        } else {
            onMounted(() => {
                this.renderFileName();
            });
        }
    }

    //--------------------------------------------------------------------------
    // Migration
    //--------------------------------------------------------------------------

    /**
     * While the way to upgrade knowledge articles has not been decided, the
     * upgrade method will be used to adjust Behavior props to the latest
     * requirements.
     *
     * This method is used to extract information from existing `/file`
     * elements that were saved in the database before the introduction of
     * the FileViewer usage, and convert them to the new fileData prop.
     * Notably, the attachment ID, the access token and the checksum are
     * extracted from the href, only if the url matches the current domain.
     * An example of a previously saved structure is the following:
     *      <div class="o_knowledge_behavior_anchor o_knowledge_behavior_type_file">
     *          <div data-prop-name="fileImage">
     *              <a href="https://example.com/web/content/1?unique=aaa&access_token=bbb&download=true"
     *                  data-mimetype="image/jpeg" class="o_image"></a>
     *          </div>
     *          <div data-prop-name="fileName">name.jpg</div>
     *          <div data-prop-name="fileExtension">jpg</div>
     *      </div>
     */
    upgradeKnowledgeBehavior() {
        if (this.props.fileData) {
            // FileBehavior is already updated to latest version, nothing to do
            this.fileData = this.props.fileData;
            return;
        }
        // `fileName` and `fileExtension` were html props under `data-prop-name`
        // and now are stored as text in behaviorProps. Ensure that their value
        // are not Markup objects.
        const fileName = String(this.props.fileName || '');
        const fileExtension = String(this.props.fileExtension || '');
        // Craft the file prop (which should be mandatory) if not present.
        const blueprint = this.props.anchor.cloneNode(false);
        blueprint.replaceChildren(...this.props.blueprintNodes);
        const htmlFileImageLink = getPropNameNode('fileImage', blueprint).querySelector('a');
        const href = htmlFileImageLink.getAttribute("href");
        const mimetype = htmlFileImageLink.dataset.mimetype;
        let accessToken, checksum, id, type, url;
        if (href.startsWith(getOrigin())) {
            id = parseInt((href.match(/\/web\/(?:content|image)\/(\d+)/) || [])[1]);
            checksum = (href.match(/unique=([^&]+)/) || [])[1];
            accessToken = (href.match(/access_token=([^&]+)/) || [])[1];
        }
        if (!id) {
            type = "url";
            url = href.replace(/\?.*$/, "");
        } else {
            type = "binary";
        }
        const defaultName = _t("untitled");
        this.fileData = {
            accessToken,
            checksum,
            extension: fileExtension,
            filename: fileName || defaultName,
            id,
            mimetype,
            name: fileName || defaultName,
            type,
            url,
        };
        // Overwrite existing behavior props with the only final prop: fileData.
        this.props.anchor.dataset.behaviorProps = encodeDataBehaviorProps({
            fileData: this.fileData,
        });
    }

    //--------------------------------------------------------------------------
    // TECHNICAL
    //--------------------------------------------------------------------------

    /**
     * @override
     * Render the fileName just before the Behavior is inserted in the editor.
     * @see AbstractBehavior for the full explanation.
     */
    extraRender() {
        super.extraRender();
        this.renderFileName();
    }

    /**
     * @override
     * Ensure that behavior props stored in the data-behavior-props attribute
     * of the anchor of this Behavior are up to date with the latest
     * implementation. @see AbstractBehavior for the full explanation.
     */
    setupAnchor() {
        super.setupAnchor();
        // TODO ABD remove when the upgrade procedure has been decided.
        this.upgradeKnowledgeBehavior();
    }

    /**
     * @override
     * The fileNameRef nodes have to be shared in collaboration but are not
     * directly an html prop of this Behavior, hence this override to set their
     * oids. @see AbstractBehavior for the full explanation.
     */
    synchronizeOids(blueprint) {
        super.synchronizeOids(blueprint);
        const currentFileNameEl = this.props.anchor.querySelector('.o_knowledge_file_name_container[data-oe-protected="false"]');
        const blueprintFileNameEl = blueprint.querySelector('.o_knowledge_file_name_container[data-oe-protected="false"]');
        if (!blueprintFileNameEl) {
            return;
        }
        copyOids(blueprintFileNameEl, currentFileNameEl);
    }

    //--------------------------------------------------------------------------
    // GETTERS/SETTERS
    //--------------------------------------------------------------------------

    /**
     * @returns {String} fileName as it is written in the editor.
     */
    get fileNameSpanTextContent() {
        return this.fileNameRef.el.querySelector(".o_knowledge_file_name")?.textContent || "";
    }

    //--------------------------------------------------------------------------
    // BUSINESS
    //--------------------------------------------------------------------------

    renameFile() {
        let newName = this.nameInput.el.value;
        if (newName.length) {
            this.setFileName(newName);
            return true;
        }
        return false;
    }

    renderFileName() {
        const fileNameEl = renderToElement("knowledge.FileBehaviorFileName", {
            fileName: this.state.fileModel.filename,
        });
        this.fileNameRef.el.replaceChildren(fileNameEl);
    }

    setFileName(newName) {
        if (newName === this.state.fileModel.filename) {
            return;
        }
        // filename is the name of the file as written in the editor by the
        // user. It does not necessarily have the file extension.
        this.state.fileModel.filename = newName;
        if (this.state.fileModel.extension) {
            const pattern = new RegExp(`\\.${this.state.fileModel.extension}$`, 'i');
            if (!newName.match(pattern)) {
                newName += `.${this.state.fileModel.extension}`;
            }
        }
        // name is the full name of the file (always with extension)
        // and is used as the url queryParam when downloading it.
        this.state.fileModel.name = newName;
        const props = decodeDataBehaviorProps(this.props.anchor.dataset.behaviorProps);
        props.fileData = this.state.fileModel;
        this.props.anchor.dataset.behaviorProps = encodeDataBehaviorProps(props);
    }

    //--------------------------------------------------------------------------
    // HANDLERS
    //--------------------------------------------------------------------------

    onBlurNameInput(ev) {
        this.renameFile();
        this.state.editFileName = false;
    }

    /**
     * Callback function called when the user clicks on the "Send as Message" button.
     * The function will execute a macro that will open the last opened form view,
     * compose a new message and attach the associated file to it.
     * @param {Event} ev
     */
    async onClickAttachToMessage(ev) {
        const dataTransfer = new DataTransfer();
        try {
            const response = await window.fetch(this.state.fileModel.urlRoute);
            const blob = await response.blob();
            const file = new File([blob], this.state.fileModel.name, {
                type: blob.type
            });
            /**
             * dataTransfer will be used to mimic a drag and drop of
             * the file in the target record chatter.
             * @see KnowledgeMacro
             */
            dataTransfer.items.add(file);
        } catch {
            return;
        }
        const macro = new AttachToMessageMacro({
            targetXmlDoc: this.targetRecordInfo.xmlDoc,
            breadcrumbs: this.targetRecordInfo.breadcrumbs,
            data: {
                dataTransfer: dataTransfer,
            },
            services: this.macrosServices,
        });
        macro.start();
    }

    /**
     * Callback function called when the user clicks on the "Download" button.
     * The function will simply open a link that will trigger the download of
     * the associated file. If the url is not valid, the function will display
     * an error message.
     * @param {Event} ev
     */
    async onClickDownload(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        try {
            await downloadFile(this.state.fileModel.downloadUrl);
        } catch {
            this.dialogService.add(AlertDialog, {
                body: _t(
                    'Oops, the file %s could not be found. Please replace this file box by a new one to re-upload the file.',
                    this.state.fileModel.name
                ),
                title: _t('Missing File'),
                confirm: () => {},
                confirmLabel: _t('Close'),
            });
        }
    }

    onClickFileImage(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        if (this.state.fileModel.isViewable) {
            this.attachmentViewer.open(this.state.fileModel);
        }
    }

    /**
     * Callback function called when the user clicks on the "Use As Attachment" button.
     * The function will execute a macro that will open the last opened form view
     * and add the associated file to the attachments of the chatter.
     * @param {Event} ev
     */
    async onClickUseAsAttachment(ev) {
        let attachment;
        try {
            const response = await window.fetch(this.state.fileModel.urlRoute);
            const blob = await response.blob();
            const dataURL = await getDataURLFromFile(blob);
            attachment = await this.rpcService('/web_editor/attachment/add_data', {
                name: this.state.fileModel.name,
                data: dataURL.split(',')[1],
                is_image: false,
                res_id: this.targetRecordInfo.resId,
                res_model: this.targetRecordInfo.resModel,
            });
        } catch {
            return;
        }
        if (!attachment) {
            return;
        }
        const macro = new UseAsAttachmentMacro({
            targetXmlDoc: this.targetRecordInfo.xmlDoc,
            breadcrumbs: this.targetRecordInfo.breadcrumbs,
            data: null,
            services: this.macrosServices,
        });
        macro.start();
    }

    onFocusFileName(ev) {
        this.state.editFileName = true;
    }

    onKeydownNameInput(ev) {
        ev.stopPropagation();
        if (ev.key !== "Enter") {
            return;
        } else {
            ev.preventDefault();
        }
        if (this.renameFile()) {
            this.state.editFileName = false;
            const afterFilePos = rightPos(this.props.anchor);
            setSelection(...afterFilePos, ...afterFilePos, true);
        }
    }
}
