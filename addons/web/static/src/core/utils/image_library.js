    export async function save(env, { attachments, targetRecord, targetFieldName, convertToWebp = false, changeRecordName = true }){
        const targetFieldType = targetRecord.config.fields[targetFieldName].type;
        const attachmentRecords = await retrieveAttachmentRecords(env, { attachmentIds: attachments.map((attachment) => attachment.id)});
        for (const attachmentRecord of attachmentRecords){
            if (!attachmentRecord.datas) {
                return notifyURLAttachmentUploadFailed(env, { attachmentName: attachmentRecord.name });
            }
            if (
                convertToWebp &&
                !["image/gif", "image/svg+xml"].includes(attachmentRecord.mimetype)
            ) {
                await convertToWebpFormat(env, { attachmentRecord });
            }
            if (targetFieldType === "binary"){
                await updateBinary({ attachmentRecord, targetRecord, targetFieldName, changeRecordName });
            }
            else if (targetFieldType === "one2many" || targetFieldType === "many2many"){
                await updateX2Many({ attachmentRecord, targetRecord, targetFieldName });
            }
            else {
                throw new Error("Not Implemented")
            }
        }
    }

    async function retrieveAttachmentRecords(env, { attachmentIds }){
        return await env.services.orm.searchRead(
            "ir.attachment",
            [["id", "in", attachmentIds]],
            ["id", "datas", "name", "mimetype"],
            {}
        );
    }

    function notifyURLAttachmentUploadFailed(env, { attachmentName }){
        // URL type attachments are mostly demo records which don't have any ir.attachment datas
        // TODO: make it work with URL type attachments
        return env.services.notification.add(
            `Cannot add URL type attachment "${attachmentName}". Please try to reupload this image.`,
            {
                type: "warning",
            }
        );
    }

    export async function convertToWebpFormat(env, { attachmentRecord }){
        // This method is widely adapted from onFileUploaded in ImageField.
        // Upon change, make sure to verify whether the same change needs
        // to be applied on both sides.
        // Generate alternate sizes and format for reports.
        const image = document.createElement("img");
        image.src = `data:${attachmentRecord.mimetype};base64,${attachmentRecord.datas}`;
        await new Promise((resolve) => image.addEventListener("load", resolve));

        const originalSize = Math.max(image.width, image.height);
        const smallerSizes = [1024, 512, 256, 128].filter((size) => size < originalSize);
        let referenceId = undefined;

        for (const size of [originalSize, ...smallerSizes]) {
            const ratio = size / originalSize;
            const canvas = document.createElement("canvas");
            canvas.width = image.width * ratio;
            canvas.height = image.height * ratio;
            const ctx = canvas.getContext("2d");
            ctx.drawImage(
                image,
                0,
                0,
                image.width,
                image.height,
                0,
                0,
                canvas.width,
                canvas.height
            );

            // WebP format
            const webpData = canvas.toDataURL("image/webp", 0.75).split(",")[1];
            const [resizedId] = await env.services.orm.call("ir.attachment", "create_unique", [
                [
                    {
                        name: attachmentRecord.name.replace(/\.[^/.]+$/, ".webp"),
                        description: size === originalSize ? "" : `resize: ${size}`,
                        datas: webpData,
                        res_id: referenceId,
                        res_model: "ir.attachment",
                        mimetype: "image/webp",
                    },
                ],
            ]);

            referenceId = referenceId || resizedId;

            // JPEG format for compatibility
            const jpegData = canvas.toDataURL("image/jpeg", 0.75).split(",")[1];
            await env.services.orm.call("ir.attachment", "create_unique", [
                [
                    {
                        name: attachmentRecord.name.replace(/\.[^/.]+$/, ".jpg"),
                        description: `resize: ${size} - format: jpeg`,
                        datas: jpegData,
                        res_id: resizedId,
                        res_model: "ir.attachment",
                        mimetype: "image/jpeg",
                    },
                ],
            ]);
        }
        const canvas = document.createElement("canvas");
        canvas.width = image.width;
        canvas.height = image.height;
        const ctx = canvas.getContext("2d");
        ctx.drawImage(image, 0, 0, image.width, image.height);

        const webpData = canvas.toDataURL("image/webp", 0.75).split(",")[1];
        attachmentRecord.datas = webpData;
        attachmentRecord.mimetype = "image/webp";
        attachmentRecord.name = attachmentRecord.name.replace(/\.[^/.]+$/, ".webp");
    }

    export async function updateBinary({ attachmentRecord, targetRecord, targetFieldName, changeRecordName }){
        let update_data = {
            [targetFieldName]: attachmentRecord.datas,
        }
        if (changeRecordName){
            update_data['name'] = attachmentRecord.name
        }
        await targetRecord.update(update_data);
    }

    export async function updateX2Many({ attachmentRecord, targetRecord, targetFieldName, changeRecordName }){
        const imageList = targetRecord.data[targetFieldName];
        const activeFields = imageList.activeFields;
        const supportedFields = ["image_1920", "image_1024", "image_512", "image_256", "image_128"];
        imageList.addNewRecord({ position: "bottom" }).then((record) => {
            const updateData = {};
            for (const field in activeFields) {
                if (attachmentRecord.datas && supportedFields.includes(field)) {
                    updateData[field] = attachmentRecord.datas;
                    if (changeRecordName){
                        updateData["name"] = attachmentRecord.name;
                    }
                }
            }
            record.update(updateData);
        });
    }
