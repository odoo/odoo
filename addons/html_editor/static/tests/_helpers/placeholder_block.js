import { unformat } from "./format";

export const PLACEHOLDER_BLOCK_CONTAINER = (
    side,
    baseContainerNodeName = "P",
    baseContainerClass = "o-paragraph"
) =>
    unformat(
        `<div class="o-placeholder-block-container" contenteditable="false">
            <${baseContainerNodeName.toLowerCase()} class="o-placeholder-block-${side}${
            baseContainerClass ? " " + baseContainerClass : ""
        }" contenteditable="true">
                <br>
            </${baseContainerNodeName.toLowerCase()}>
        </div>`
    );
