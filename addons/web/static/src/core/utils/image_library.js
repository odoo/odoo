export async function saveSingleAttachment(
    env,
    { attachment, targetRecord, targetFieldName, changeRecordName, setAttachmentId }
) {
    const attachmentRecord = (
        await retrieveAttachmentRecords(env, { attachmentIds: [attachment.id] })
    )[0];
    if (!attachmentRecord.raw) {
        return notifyURLAttachmentUploadFailed(env, { attachmentName: attachmentRecord.name });
    }

    const update_data = {};
    if (setAttachmentId) {
        update_data[targetFieldName] = attachmentRecord;
    } else {
        update_data[targetFieldName] = attachmentRecord.raw;
        if (changeRecordName) {
            update_data["name"] = attachmentRecord.name;
        }
    }
    await targetRecord.update(update_data);
}

export async function saveMultipleAttachments(
    env,
    { attachments, targetRecord, targetFieldName, convertToWebp, setAttachmentId, forceCreate }
) {
    const imageList = targetRecord.data[targetFieldName];
    const supportedFields = ["image_1920", "image_1024", "image_512", "image_256", "image_128"];
    const attachmentRecords = await retrieveAttachmentRecords(env, {
        attachmentIds: attachments.map((attachment) => attachment.id),
    });
    for (const attachmentRecord of attachmentRecords) {
        if (!attachmentRecord.raw) {
            return notifyURLAttachmentUploadFailed(env, { attachmentName: attachmentRecord.name });
        }
        if (convertToWebp && !["image/gif", "image/svg+xml"].includes(attachmentRecord.mimetype)) {
            await convertToWebpFormat(env, { attachmentRecord });
        }
        const activeFields = imageList.activeFields;
        const updateData = {};
        if (setAttachmentId) {
            updateData["attachment_id"] = attachmentRecord.id;
        } else {
            for (const field in activeFields) {
                if (attachmentRecord.raw && supportedFields.includes(field)) {
                    updateData[field] = attachmentRecord.raw;
                    updateData["name"] = attachmentRecord.name;
                }
            }
        }

        if (forceCreate) {
            imageList.linkTo(
                await env.services.orm.call(imageList._config.resModel, "create", [updateData])
            );
        } else {
            const record = await imageList.addNewRecord({ position: "bottom" });
            await record.update(updateData);
        }
    }
}

/**
 * Generates WebP and JPEG variants of an image at multiple resolutions.
 *
 * @param {Object} params
 * @param {Object} params.source Image source: `{ url }` or `{ data, mimetype }`
 * @param {string} params.name Base filename; extension is replaced with `.webp` / `.jpg`
 * @param {number[]} [params.sizes=[1920,1024,512,256,128]] Max dimensions to generate
 * @param {false|"low"|"medium"|"high"} [params.smoothing=false] Canvas interpolation quality
 * @returns {Promise<Object[]>} Variant objects suitable for `ir.attachment.web_create_image_variants`
 */
export async function generateImageVariants({
    source,
    name,
    sizes = [1920, 1024, 512, 256, 128],
    smoothing = false,
}) {
    const { url, data, mimetype } = source || {};
    const webpName = name.replace(/\.[^/.]+$/, ".webp");
    const jpegName = name.replace(/\.[^/.]+$/, ".jpg");
    const image = document.createElement("img");
    image.src = url || `data:${mimetype};base64,${data}`;
    await new Promise((resolve) => image.addEventListener("load", resolve));

    const originalSize = Math.max(image.width, image.height);
    const smallerSizes = sizes.filter((size) => size < originalSize);
    const variants = [];
    for (const size of [originalSize, ...smallerSizes]) {
        const ratio = size / originalSize;
        const canvas = document.createElement("canvas");
        canvas.width = image.width * ratio;
        canvas.height = image.height * ratio;
        const ctx = canvas.getContext("2d");
        ctx.fillStyle = "transparent";
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.imageSmoothingEnabled = !!smoothing;
        if (smoothing) {
            ctx.imageSmoothingQuality = smoothing;
        }
        ctx.drawImage(image, 0, 0, image.width, image.height, 0, 0, canvas.width, canvas.height);

        const isOriginalSize = size === originalSize;
        const sizePrefix = isOriginalSize ? "" : `resize: ${size}`;
        variants.push({
            images: [
                {
                    name: webpName,
                    description: `${sizePrefix}`,
                    raw:
                        isOriginalSize && mimetype === "image/webp"
                            ? data
                            : canvas.toDataURL("image/webp", 0.75).split(",")[1],
                    mimetype: "image/webp",
                },
                {
                    name: jpegName,
                    description: `${sizePrefix} - format: jpeg`,
                    raw: canvas.toDataURL("image/jpeg", 0.75).split(",")[1],
                    mimetype: "image/jpeg",
                },
            ],
        });
    }
    return variants;
}

async function retrieveAttachmentRecords(env, { attachmentIds }) {
    return await env.services.orm.searchRead(
        "ir.attachment",
        [["id", "in", attachmentIds]],
        ["id", "raw", "name", "mimetype"],
        {}
    );
}

function notifyURLAttachmentUploadFailed(env, { attachmentName }) {
    // URL type attachments are mostly demo records which don't have any ir.attachment raw
    // TODO: make it work with URL type attachments
    return env.services.notification.add(
        `Cannot add URL type attachment "${attachmentName}". Please try to reupload this image.`,
        {
            type: "warning",
        }
    );
}

async function convertToWebpFormat(env, { attachmentRecord }) {
    // This method is widely adapted from onFileUploaded in ImageField.
    // Upon change, make sure to verify whether the same change needs
    // to be applied on both sides.
    // Generate alternate sizes and format for reports.
    const variants = await generateImageVariants({
        source: { data: attachmentRecord.raw, mimetype: attachmentRecord.mimetype },
        name: attachmentRecord.name,
        sizes: [1024, 512, 256, 128],
    });
    await env.services.orm.call("ir.attachment", "web_create_image_variants", [variants]);
    const webpData = variants[0]?.images?.[0]?.raw;
    attachmentRecord.raw = webpData;
    attachmentRecord.mimetype = "image/webp";
    attachmentRecord.name = attachmentRecord.name.replace(/\.[^/.]+$/, ".webp");
}
