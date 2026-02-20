    import { ImageSelector } from "@html_editor/main/media/media_dialog/image_selector";

    export async function createImageHTMLNode(orm, { newImageAttachment, oldImageNode = null }){
        if (!newImageAttachment){
            throw new Error("newImageAttachment is required.");
        }
        const newImageNode = await _createImageHTMLNode(orm, { newImageAttachment });
        if (oldImageNode){
            _copyOldImageNodeAttributes({ oldImageNode, newImageNode });
        }
        _cleanupAndApplyMediaClasses({ newImageNode });
        return newImageNode;
    }

    async function _createImageHTMLNode(orm, { newImageAttachment }){
        newImageAttachment.mediaType = 'attachment';
        let node = await ImageSelector.createElements(
            [newImageAttachment],
            { orm: orm }
        );
        return node[0];
    };

    function _copyOldImageNodeAttributes({ oldImageNode, newImageNode }){
        if (!oldImageNode || !newImageNode){
            return;
        };
        newImageNode.classList.add(...oldImageNode.classList);
        const style = oldImageNode.getAttribute("style");
        if (style) {
            newImageNode.setAttribute("style", style);
        }
        const datasetAttributesToCopy = [
            "shape",
            "shapeColors",
            "shapeFlip",
            "shapeRotate",
            "hoverEffect",
            "hoverEffectColor",
            "hoverEffectStrokeWidth",
            "hoverEffectIntensity",
        ];
        for (const attribute in datasetAttributesToCopy){
            if (oldImageNode["dataset"][attribute]){
                newImageNode["dataset"][attribute] = oldImageNode["dataset"][attribute];
            }
        }
    };

    function _cleanupAndApplyMediaClasses({ newImageNode }){
        newImageNode.classList.remove("o_modified_image_to_save");
        newImageNode.classList.remove("oe_edited_link");
        newImageNode.classList.add(...ImageSelector.mediaSpecificClasses);
    };
